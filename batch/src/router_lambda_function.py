import json
import boto3
import re
import csv
import os
import logging
from io import BytesIO, StringIO
from ods_patterns import ODS_PATTERNS
# Incoming file format DISEASETYPE_Vaccinations_version_ODSCODE_DATETIME.csv
# for example: Flu_Vaccinations_v5_YYY78_20240708T12130100.csv - ODS code has multiple lengths
logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3_client = boto3.client('s3', region_name='eu-west-2')
sqs_client = boto3.client('sqs', region_name='eu-west-2')


def get_environment():
    return os.getenv("ENVIRONMENT")


def extract_ods_code(file_key):
    supplier_match = re.search(r'_Vaccinations_v\d+_(\w+)_\d+T\d+\.csv$', file_key)
    return supplier_match.group(1) if supplier_match else None


def identify_supplier(ods_code):
    return ODS_PATTERNS.get(ods_code, None)


def identify_disease_type(file_key):
    disease_match = re.search(r'^(\w+)_Vaccinations_', file_key)
    return disease_match.group(1) if disease_match else None


def identify_timestamp(file_key):
    timestamp_match = re.search(r'_(\d+T\d+)\.csv$', file_key)
    return timestamp_match.group(1) if timestamp_match else None


def initial_file_validation(file_key, bucket_name):
    # TO DO- Placeholder for initial file validation logic, currently populated with example
    if "invalid" in file_key:
        return False, ["Invalid content detected"]
    elif "missing" in file_key:
        return False, ["Missing required fields"]
    else:
        return True, []
        # Temporary placeholder for validation success


def send_to_supplier_queue(supplier, message_body):
    # TO DO - will not send as no queue exists, only logs the error for now
    account_id = os.getenv("ACCOUNT_ID")

    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{account_id}/{supplier}_metadata_queue"
    print(queue_url)

    try:
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
        logger.info(f"Message sent to SQS queue for supplier {supplier}")
    except sqs_client.exceptions.QueueDoesNotExist:
        logger.error(f"queue {queue_url} does not exist")
        return False
    return True


def create_ack_file(bucket_name, file_key, ack_bucket_name, validation_passed, validation_errors):
    # TO DO - Populate acknowledgement file with correct values once known
    headers = ['MESSAGE_HEADER_ID', 'HEADER_RESPONSE_CODE', 'ISSUE_SEVERITY', 'ISSUE_CODE', 'RESPONSE_TYPE',
               'RESPONSE_CODE', 'RESPONSE_DISPLAY', 'RECEIVED_TIME', 'MAILBOX_FROM', 'LOCAL_ID']
    # Placeholder for data rows for success
    if validation_passed:
        data_rows = [['Value1', 'Value2', 'Value3', 'Value4', 'Value5',
                     'Value6', 'Value7', 'Value8', 'Value9', 'Value10']]
        parts = file_key.split('.')
        ack_filename = (f"{parts[0]}_response.csv")
    # Placeholder for data rows for errors
    else:
        data_rows = [
            ['Value1', 'Error2', 'Value3', 'Error4', 'Value5',
             'Value6', 'Value7', 'Value8', 'Value9', 'Value10']]
        # construct acknowledgement file
        parts = file_key.split('.')
        ack_filename = (f"{parts[0]}_response.csv")
        print(f"{data_rows}")
    # Create CSV file with | delimiter, filetype .csv
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, delimiter='|')
    csv_writer.writerow(headers)
    csv_writer.writerows(data_rows)
    # Upload the CSV.zip file to S3
    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)
    print(f"{ack_bucket_name}")
    print(f"{data_rows}")
    logger.info(f"Uploaded acknowledgement file to {ack_bucket_name}")


def lambda_handler(event, context):
    error_files = []

    for record in event['Records']:
        try:
            bucket_name = record['s3']['bucket']['name']
            file_key = record['s3']['object']['key']
            ods_code = extract_ods_code(file_key)
            disease_type = identify_disease_type(file_key)
            timestamp = identify_timestamp(file_key)
            supplier = identify_supplier(ods_code)
            print(f"{supplier}")
            if not supplier and ods_code:
                logging.error(f"Supplier not found for ods code {ods_code}")
            # TO DO- Perform initial file validation
            validation_passed, validation_errors = initial_file_validation(file_key, bucket_name)
            # Determine ack_bucket_name based on environment
            ack_bucket_name = os.getenv("ACK_BUCKET_NAME")
            # Create acknowledgment file
            create_ack_file(bucket_name, file_key, ack_bucket_name, validation_passed, validation_errors)
            # if validation passed, send message to SQS queue
            if validation_passed:
                message_body = {
                    'disease_type': disease_type,
                    'supplier': supplier,
                    'timestamp': timestamp
                }
                try:
                    send_to_supplier_queue(supplier, message_body)
                except Exception:
                    logger.error(f"failed to send message to {supplier}_queue")

            logger.info(f"File Metadata processed successfully for - {file_key}")

        # Error handling for file processing
        except ValueError as ve:
            logging.error(f"Error in initial_file_validation'{file_key}': {str(ve)}")
            create_ack_file(bucket_name, file_key, ack_bucket_name, False, [str(ve)])
        except Exception as e:
            logging.error(f"Error processing file'{file_key}': {str(e)}")
            create_ack_file(bucket_name, file_key, ack_bucket_name, False, [str(e)])
            error_files.append(file_key)

    if error_files:
        logger.error(f"Processing errors occurred for the following files: {', '.join(error_files)}")

    logger.info("Completed processing all file metadata in current batch")
    return {
        'statusCode': 200,
        'body': json.dumps('File processing for S3 bucket completed')
    }
