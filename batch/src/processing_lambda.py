import boto3
import csv
import json
from io import StringIO, BytesIO
import os
from convert_fhir_json import convert_to_fhir_json
from get_imms_id import ImmunizationApi
import logging
from ods_patterns import SUPPLIER_SQSQUEUE_MAPPINGS

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
logger = logging.getLogger()


def get_environment():
    _env = os.getenv("ENVIRONMENT")
    non_prod = ["internal-dev", "int", "ref", "sandbox"]
    if _env in non_prod:
        return _env
    elif _env == "prod":
        return "prod"
    else:
        return "internal-dev"  # default to internal-dev for pr and user workspaces


def send_to_sqs(supplier, message_body):
    """Send a message to the specified SQS queue."""
    # Send a message to the supplier queue
    imms_env = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")
    SQS_name = SUPPLIER_SQSQUEUE_MAPPINGS.get(supplier, supplier)
    if "prod" in imms_env or "production" in imms_env:
        account_id = os.getenv("PROD_ACCOUNT_ID")
    else:
        account_id = os.getenv("LOCAL_ACCOUNT_ID")
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{account_id}/{imms_env}-{SQS_name}-processingdata-queue.fifo"
    logger.error(f"Queue_URL: {queue_url}")

    try:
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            MessageGroupId="default",
        )
        logger.info(f"Message sent to SQS queue '{SQS_name}' for supplier {supplier}")
    except sqs_client.exceptions.QueueDoesNotExist:
        logger.error(f"queue {queue_url} does not exist")
        return False
    return True


def fetch_file_from_s3(bucket_name, file_key):
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return response['Body'].read().decode('utf-8')


def write_to_ack_file(ack_bucket_name, ack_filename, data_row):
    csv_buffer = BytesIO()
    s3_client.download_fileobj(ack_bucket_name, ack_filename, csv_buffer)
    csv_buffer.seek(0)
    existing_data = csv_buffer.read().decode('utf-8')
    csv_buffer = StringIO(existing_data)
    csv_writer = csv.writer(csv_buffer, delimiter='|')
    csv_writer.writerow(data_row)

    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)
    logger.error(f"Ack file updated to {ack_bucket_name}: {ack_filename}")


def process_csv_to_fhir(bucket_name, file_key, supplier, vaccine_type, ack_bucket_name):
    csv_data = fetch_file_from_s3(bucket_name, file_key)
    csv_reader = csv.DictReader(StringIO(csv_data), delimiter='|')
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at = response['LastModified']
    created_at_formatted = created_at.strftime("%Y%m%dT%H%M%S00")

    headers = ['MESSAGE_HEADER_ID', 'HEADER_RESPONSE_CODE', 'ISSUE_SEVERITY', 'ISSUE_CODE', 'RESPONSE_TYPE',
               'RESPONSE_CODE', 'RESPONSE_DISPLAY', 'RECEIVED_TIME', 'MAILBOX_FROM', 'LOCAL_ID', 'MESSAGE_DELIVERY']
    parts = file_key.split('.')
    ack_filename = f"processedFile/{parts[0]}_response.csv"

    # Create the initial ack file with headers
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, delimiter='|')
    csv_writer.writerow(headers)
    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)

    row_count = 0  # Initialize a counter for rows

    for row in csv_reader:
        row_count += 1  # Increment the counter for each row
        if row.get('ACTION_FLAG') in {"new", "update", "delete"} and row.get('UNIQUE_ID_URI') and row.get('UNIQUE_ID'):

            fhir_json, valid = convert_to_fhir_json(row, vaccine_type)
            if valid:
                identifier_system = row.get('UNIQUE_ID_URI')
                action_flag = row.get('ACTION_FLAG')
                identifier_value = row.get('UNIQUE_ID')
                logger.error(f"Successfully converted row to FHIR: {fhir_json}")
                flag = True
                if action_flag in ("delete", "update"):
                    flag = False
                    response, status_code = ImmunizationApi.get_imms_id(identifier_system, identifier_value)
                    if response.get("total") == 1 and status_code == 200:
                        flag = True
                if flag:
                    # Prepare the message for SQS
                    if action_flag == "new":
                        message_body = {
                            'fhir_json': fhir_json,
                            'action_flag': action_flag,
                        }
                    if action_flag in ("delete", "update"):
                        entry = response.get("entry", [])[0]
                        imms_id = entry["resource"].get("id")
                        version = entry["resource"].get("meta", {}).get("versionId")
                        message_body = {
                            'fhir_json': fhir_json,
                            'action_flag': action_flag,
                            'imms_id': imms_id,
                            "version": version
                        }
                    status = send_to_sqs(supplier, message_body)
                    if status:
                        data_row = ['TBC', 'ok', 'information', 'informational', 'business',
                                    '20013', 'Success', created_at_formatted, 'TBC', 'DPS', True]
                    else:
                        logger.error("Error sending to SQS")
                        data_row = ['TBC', 'fatal-error', 'error', 'error', 'business',
                                    '20005', 'Error sending to SQS', created_at_formatted, 'TBC', 'DPS', False]
                else:
                    logger.error(f"imms_id not found:{response} for: {identifier_system}#{identifier_value}"
                                 F"and status_code:{status_code}")
                    data_row = ['TBC', 'fatal-error', 'error', 'error', 'business',
                                '20005', 'Unsupported file type received as an attachment', created_at_formatted,
                                'TBC', 'DPS', False]
            else:
                logger.error(f"Invalid FHIR conversion for row: {row}")
                data_row = ['TBC', 'fatal-error', 'error', 'error', 'business',
                            '20005', 'Unsupported file type received as an attachment', created_at_formatted,
                            'TBC', 'DPS', False]
        else:
            logger.error(f"Invalid FHIR conversion for row: {row}")
            data_row = ['TBC', 'fatal-error', 'error', 'error', 'business',
                        '20005', 'Unsupported file type received as an attachment', created_at_formatted,
                        'TBC', 'DPS', False]

        # Write the data row to the ack file
        write_to_ack_file(ack_bucket_name, ack_filename, data_row)

    logger.error(f"Total rows processed: {row_count}")  # logger.error the total number of rows processed


def process_lambda_handler(event, context):
    imms_env = get_environment()
    bucket_name = os.getenv("ACK_BUCKET_NAME", f'immunisation-batch-{imms_env}-batch-data-source')
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f'immunisation-batch-{imms_env}-batch-data-destination')

    for record in event['Records']:
        try:
            message_body = json.loads(record['body'])
            vaccine_type = message_body.get('vaccine_type')
            supplier = message_body.get('supplier')
            file_key = message_body.get('filename')
            process_csv_to_fhir(bucket_name, file_key, supplier, vaccine_type, ack_bucket_name)

        except Exception as e:
            logger.error(f"Error processing message: {e}")


if __name__ == "__main__":
    process_lambda_handler({'Records': []}, {})
