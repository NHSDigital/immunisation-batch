import boto3
import csv
import json
from io import StringIO, BytesIO
import os
from convert_fhir_json import convert_to_fhir_json
from get_imms_id import ImmunizationApi

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')


def get_environment():
    _env = os.getenv("ENVIRONMENT")
    non_prod = ["internal-dev", "int", "ref", "sandbox"]
    if _env in non_prod:
        return _env
    elif _env == "prod":
        return "prod"
    else:
        return "internal-dev"  # default to internal-dev for pr and user workspaces


def send_to_sqs(queue_url, message_body):
    """Send a message to the specified SQS queue."""
    response = sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message_body)
    )
    return response


def fetch_file_from_s3(bucket_name, file_key):
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return response['Body'].read().decode('utf-8')


def create_ack_file(file_key, ack_bucket_name, results, created_at_formatted):
    headers = ['MESSAGE_HEADER_ID', 'HEADER_RESPONSE_CODE', 'ISSUE_SEVERITY', 'ISSUE_CODE', 'RESPONSE_TYPE',
               'RESPONSE_CODE', 'RESPONSE_DISPLAY', 'RECEIVED_TIME', 'MAILBOX_FROM', 'LOCAL_ID']
    parts = file_key.split('.')
    ack_filename = f"processedFile/{parts[0]}_response.csv"

    data_rows = []
    for result in results:
        if result['valid']:
            data_row = ['TBC', 'ok', 'information', 'informational', 'business',
                        '20013', 'Success', created_at_formatted, 'TBC', 'DPS']
        else:
            data_row = ['TBC', 'fatal-error', 'error', 'error', 'business',
                        '20005', result['message'], created_at_formatted, 'TBC', 'DPS']
        data_rows.append(data_row)

    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, delimiter='|')
    csv_writer.writerow(headers)
    csv_writer.writerows(data_rows)

    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))
    print(csv_bytes)
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)
    print(f"Ack file uploaded to {ack_bucket_name}: {ack_filename}")


def process_csv_to_fhir(bucket_name, file_key, sqs_queue_url, vaccine_type, ack_bucket_name):
    csv_data = fetch_file_from_s3(bucket_name, file_key)
    csv_reader = csv.DictReader(StringIO(csv_data), delimiter='|')
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at = response['LastModified']
    created_at_formatted = created_at.strftime("%Y%m%dT%H%M%S00")

    results = []
    for row in csv_reader:

        if row.get('ACTION_FLAG') and row.get('ACTION_FLAG') in ("new", "update", "delete") and row.get('UNIQUE_ID_URI') and row.get('UNIQUE_ID'):  # Check if 'ACTION_FLAG' is not empty
            fhir_json, valid = convert_to_fhir_json(row, vaccine_type)
            if valid:
                identifier_system = row.get('UNIQUE_ID_URI')
                action_flag = row.get('ACTION_FLAG')
                identifier_value = row.get('UNIQUE_ID')
                print(f"Successfully converted row to FHIR: {fhir_json}")
                flag = True
                if action_flag in ("delete", "update"):
                    flag = False
                    response = ImmunizationApi.get_immunization_id(identifier_system, identifier_value)
                    if response["statusCode"] == 200:
                        flag = True
                if flag:
                    results.append({'valid': True, 'message': 'Success'})
                    # Send the valid FHIR JSON and action flag to SQS
                    if action_flag == "new":
                        message_body = {
                            'fhir_json': fhir_json,
                            'action_flag': action_flag,
                        }
                    if action_flag in ("delete", "update"):
                        body = json.loads(response["body"])
                        imms_id = body["id"]
                        version = body["Version"]
                        message_body = {
                            'fhir_json': fhir_json,
                            'action_flag': action_flag,
                            'imms_id': imms_id,
                            "version": version
                        }

                    send_to_sqs(sqs_queue_url, message_body)
                else:
                    print(f"imms_id not found:{response} for: {identifier_system}#{identifier_value}")
                    results.append({'valid': False, 'message': 'Unsupported file type received as an attachment'})
            else:
                print(f"Invalid FHIR conversion for row: {row}")
                results.append({'valid': False, 'message': 'Unsupported file type received as an attachment'})
        else:
            print(f"Invalid FHIR conversion for row: {row}")
            results.append({'valid': False, 'message': 'Unsupported file type received as an attachment'})
    create_ack_file(file_key, ack_bucket_name, results, created_at_formatted)


def process_lambda_handler(event, context):
    # Fetch message from SQS
    imms_env = get_environment()
    account_id = os.getenv(f"{imms_env.upper()}_ACCOUNT_ID")

    sqs_client = boto3.client('sqs', region_name='eu-west-2')
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{account_id}/EMIS_metadata_queue"
    sqs_queue_url = f"https://sqs.eu-west-2.amazonaws.com/{account_id}/EMIS_processing_queue"
    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1
    )

    for message in response.get('Messages', []):
        try:
            message_body = json.loads(message['Body'])
            vaccine_type = message_body.get('vaccine_type')
            supplier = message_body.get('supplier')
            timestamp = message_body.get('timestamp')
            receipt_handle = message['ReceiptHandle']

            file_key = f"{vaccine_type}_Vaccinations_v5_{supplier}_{timestamp}.csv"
            bucket_name = os.getenv("ACK_BUCKET_NAME", f'immunisation-batch-{imms_env}-batch-data-source')
            ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f'immunisation-batch-{imms_env}-batch-data-destination')
            process_csv_to_fhir(bucket_name, file_key, sqs_queue_url, vaccine_type, ack_bucket_name)

            sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
        except Exception as e:
            print(f"Error processing message: {e}")


if __name__ == "__main__":
    process_lambda_handler({}, {})
