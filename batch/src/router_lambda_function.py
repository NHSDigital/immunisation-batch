
import json
import boto3
import re
import csv
import os
import logging
from io import BytesIO, StringIO

# Incoming file format DISEASETYPE_Vaccinations_version_ODSCODE_DATETIME.csv 
# for example: Flu_Vaccinations_v5_YYY78_20240708T12130100.csv - ODS code has multiple lengths


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')


def get_environment():
    _env = os.getenv("ENVIRONMENT", "internal-dev")
    non_prod = ["internal-dev", "int", "ref", "sandbox"]
    if _env in non_prod:
        return _env
    elif _env == "prod":
        return "prod"
    else:
        return "internal-dev"  # default to internal-dev for pr and user workspaces


def identify_supplier(file_key):
    supplier_match = re.search(r'_Vaccinations_v\d+_(\w+)_\d+T\d+\.csv$', file_key)
    return supplier_match.group(1) if supplier_match else None


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
    # Need to confirm supplier queue name format - 
    imms_env = get_environment()
    ACCOUNT_ID = os.getenv(f"{imms_env.upper()}_ACCOUNT_ID")
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{ACCOUNT_ID}/{supplier}_queue"
    sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
    print(f"{queue_url}")


def create_ack_file(bucket_name, file_key, ack_bucket_name, validation_passed, validation_errors):
    #TO DO - Populate acknowledgement file with correct values once known
    headers = ['MESSAGE_HEADER_ID','HEADER_RESPONSE_CODE','ISSUE_SEVERITY','ISSUE_CODE','RESPONSE_TYPE','RESPONSE_CODE',
            'RESPONSE_DISPLAY','RECEIVED_TIME','MAILBOX_FROM','LOCAL_ID']
    
    # Placeholder for data rows for success
    if validation_passed:
        data_rows =  [['Value1', 'Value2', 'Value3', 'Value4', 'Value5',
        'Value6', 'Value7', 'Value8', 'Value9', 'Value10']]
        ack_filename = f"GP_Vaccinations_Processing_Response_v1_0_{identify_supplier(file_key)}_{identify_timestamp(file_key)}.csv"
    # Placeholder for data rows for errors
    else:
        data_rows = [
        ['Value1', 'Error2', 'Value3', 'Error4', 'Value5',
        'Value6', 'Value7', 'Value8', 'Value9', 'Value10']
        ]
        
        #construct acknowlegement file
        ack_filename = f"GP_Vaccinations_Processing_Response_v1_0_{identify_supplier(file_key)}_{identify_timestamp(file_key)}.csv"
        print(f"{data_rows}")
    # Create CSV file with | delimiter, filetype .csv
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, delimiter='|')
    csv_writer.writerow(headers)
    csv_writer.writerows(data_rows)
    
    # Upload the CSV.zip file to S3 
    #TO DO - Update file name and path of ack, Is it nested in a directory in the S3 bucket?
    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)
    print(f"{ack_bucket_name}")
    print(f"{data_rows}")
def lambda_handler(event, context):
    for record in event['Records']:
        try:
            bucket_name = record['s3']['bucket']['name']
            file_key = record['s3']['object']['key']
            supplier = identify_supplier(file_key)
            disease_type = identify_disease_type(file_key)
            timestamp = identify_timestamp(file_key)
            
            # TO DO- Perform initial file validation
            validation_passed, validation_errors = initial_file_validation(file_key, bucket_name)
            
            #Determine ack_bucket_name based on environment
            imms_env = get_environment()
            ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f'immunisation-fhir-api-{imms_env}-batch-data-destination')
            
            # Create acknowledgment file
            create_ack_file(bucket_name, file_key, ack_bucket_name, validation_passed, validation_errors)
            
            # if validation passed, send message to SQS queue
            if validation_passed:
                message_body = {
                    'disease_type': disease_type,
                    'supplier': supplier,
                    'timestamp': timestamp
                }
                send_to_supplier_queue(supplier, message_body)
            
        # Error handling for file processing
        except ValueError as ve:
            logging.error(f"Error in initial_file_validation'{file_key}': {str(ve)}")
            create_ack_file(bucket_name, file_key, ack_bucket_name, False, [str(ve)])
            
        except Exception as e:
            logging.error(f"Error processing file'{file_key}': {str(e)}")
            create_ack_file(bucket_name, file_key, ack_bucket_name, False, [str(e)])
    return {
        'statusCode': 200,
        'body': json.dumps('File processing completed')
    }
