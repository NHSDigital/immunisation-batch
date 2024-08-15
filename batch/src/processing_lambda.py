import boto3
import csv
import json
from io import StringIO
import io
import os
from convert_fhir_json import convert_to_fhir_json, dict_formation
from get_imms_id import ImmunizationApi
import logging
from ods_patterns import SUPPLIER_SQSQUEUE_MAPPINGS
from botocore.exceptions import ClientError
from constants import Constant

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
    print(f"message_body:{message_body}")
    imms_env = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")
    SQS_name = SUPPLIER_SQSQUEUE_MAPPINGS.get(supplier, supplier)
    if "prod" in imms_env or "production" in imms_env:
        account_id = os.getenv("PROD_ACCOUNT_ID")
    else:
        account_id = os.getenv("LOCAL_ACCOUNT_ID")
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{account_id}/{imms_env}-{SQS_name}-processingdata-queue.fifo"
    logger.info(f"Queue_URL: {queue_url}")

    try:
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body, ensure_ascii=False),
            MessageGroupId="default",
        )
        logger.info(f"Message sent to SQS queue '{SQS_name}' for supplier {supplier}")
    except sqs_client.exceptions.QueueDoesNotExist:
        logger.error(f"queue {queue_url} does not exist")
        return False
    except ClientError as e:
        if e.response['Error']['Code'] == 'AccessDenied':
            logger.error(f"Access denied when sending message to queue {queue_url}")
        else:
            logger.error(f"Unexpected error: {e}")
        return False
    return True


def fetch_file_from_s3(bucket_name, file_key):
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return response['Body'].read().decode('utf-8')


def process_csv_to_fhir(bucket_name, file_key, supplier, vaccine_type, ack_bucket_name):
    csv_data = fetch_file_from_s3(bucket_name, file_key)
    csv_reader = csv.DictReader(StringIO(csv_data), delimiter='|')
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at = response['LastModified']
    created_at_formatted = created_at.strftime("%Y%m%dT%H%M%S00")

    headers = Constant.header
    parts = file_key.split('.')
    ack_filename = f"processedFile/{parts[0]}_response.csv"

    accumulated_csv_content = StringIO()  # Initialize a variable to accumulate CSV content
    accumulated_csv_content.write('|'.join(headers) + '\n')  # Write the header once at the start

    row_count = 0  # Initialize a counter for rows

    for row in csv_reader:
        print(f"row:{row}")
        row_count += 1  # Increment the counter for each row
        # Split the first column which contains concatenated values
        row_values = row.get('NHS_NUMBER', '').split('|')
        # Strip quotes and handle missing values
        row_values = [value.strip('"') if value else '' for value in row_values]
        print(f"row_values:{row_values}")
        val = dict_formation(row_values)
        print(f"parsed_row:{val}")
        if val.get('ACTION_FLAG') in {"new", "update", "delete"} and val.get('UNIQUE_ID_URI') and val.get('UNIQUE_ID'):
            fhir_json, valid = convert_to_fhir_json(val, vaccine_type)
            if valid:
                identifier_system = val.get('UNIQUE_ID_URI')
                action_flag = val.get('ACTION_FLAG')
                identifier_value = val.get('UNIQUE_ID')
                print(f"Successfully converted row to FHIR: {fhir_json}")
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
                    elif action_flag in ("delete", "update"):
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
                        logger.info("message sent successfully to SQS")
                        data_row = Constant.data_rows(True, created_at_formatted)
                    else:
                        logger.error("Error sending to SQS")
                        data_row = Constant.data_rows(False, created_at_formatted)

                else:
                    print(f"imms_id not found:{response} for:{identifier_system}#{identifier_value},code:{status_code}")
                    data_row = Constant.data_rows(False, created_at_formatted)

            else:
                print(f"Invalid FHIR conversion for row: {row}")
                data_row = Constant.data_rows(False, created_at_formatted)

        else:
            print(f"Invalid row format: {row}")
            data_row = Constant.data_rows(False, created_at_formatted)

        # Convert all elements in data_row to strings
        data_row_str = [str(item) for item in data_row]

        # Write the data row to the accumulated CSV content
        accumulated_csv_content.write('|'.join(data_row_str) + '\n')

        # Upload to S3 after processing this row
        # csv_bytes = BytesIO(accumulated_csv_content.getvalue().encode('utf-8'))
        print(f"CSV content before upload:\n{accumulated_csv_content.getvalue()}")
        csv_file_like_object = io.BytesIO(accumulated_csv_content.getvalue().encode('utf-8'))
        s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
        logger.info(f"Ack file updated to {ack_bucket_name}: {ack_filename}")

    logger.info(f"Total rows processed: {row_count}")  # logger the total number of rows processed


def process_lambda_handler(event, context):
    imms_env = get_environment()
    bucket_name = os.getenv("SOURCE_BUCKET_NAME", f'immunisation-batch-{imms_env}-batch-data-source')
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f'immunisation-batch-{imms_env}-batch-data-destination')

    for record in event['Records']:
        try:
            print(f"Records:{record}")
            message_body = json.loads(record['body'])
            vaccine_type = message_body.get('vaccine_type')
            supplier = message_body.get('supplier')
            file_key = message_body.get('filename')
            process_csv_to_fhir(bucket_name, file_key, supplier, vaccine_type, ack_bucket_name)

        except Exception as e:
            logger.error(f"Error processing message: {e}")


if __name__ == "__main__":
    process_lambda_handler({'Records': []}, {})
