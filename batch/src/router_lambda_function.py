
import json 
import boto3
import re
import csv
import zipfile
from io import BytesIO

# Incoming file format DISEASETYPE_Vaccinations_version_ODSCODE_DATETIME.csv.zip 
# for example: Flu_Vaccinations_v5_ODSCODE_20240708T12130100.csv.zip

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')

def identify_supplier(file_key):
    supplier_match = re.search(r'_(\w+)_\d+\.csv\.zip$', file_key)
    return supplier_match.group(1) if supplier_match else None

def identify_disease_type(file_key):
    disease_match = re.search(r'^(\w+)_', file_key)
    return disease_match.group(1) if disease_match else None

def identify_timestamp(file_key):
    timestamp_match = re.search(r'_(\d+)\.csv\.zip$', file_key)
    return timestamp_match.group(1) if timestamp_match else None

def initial_file_validation(file_key, bucket_name):
    # TO DO- Placeholder for initial file validation logic, currently populated with example
    if "invalid" in file_key:
        return False, ["Invalid content detected"]
    elif "missing" in file_key:
        return False, ["Missing required fields"]
    else:
        return True, []  # Temporary placeholder for validation success

def send_to_supplier_queue(supplier, message_body):
    # Need to confirm supplier queue name format - 
    # Add needs environment variables for the ACCOUNT_ID
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/ACCOUNT_ID/{supplier}_queue"
    sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
    
def create_ack_file(bucket_name, file_key, ack_bucket_name, errors):
    #TO DO - Populate acknowledgement file with correct values once known
    headers = ['MESSAGE_HEADER_ID','HEADER_RESPONSE_CODE','ISSUE_SEVERITY','ISSUE_CODE','RESPONSE_TYPE','RESPONSE_CODE',
            'RESPONSE_DISPLAY','RECEIVED_TIME','MAILBOX_FROM','LOCAL_ID']
    
    # Placeholder for data rows
    data_rows = [
        ['Value1', 'Value2', 'Value3', 'Value4', 'Value5',
        'Value6', 'Value7', 'Value8', 'Value9', 'Value10']
    ]
    # Create CSV file
    #TO DO- Update filename and path once variables known, amend filetype if not .csv.zip
    csv_buffer = BytesIO()
    ack_filename = f"GP_Vaccinations_Processing_Response_v1_0_{supplier}_{timestamp}.csv"
    
    with zipfile.ZipFile(csv_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        with zipf.open(f"{file_key}.ack.csv", 'w') as csvfile:
            csv_writer = csv.writer(csvfile, delimiter='|')
            csv_writer.writerow(headers)
            csv_writer.writerows(data_rows)
    # Upload the CSV.zip file to S3 
    #TO DO - Update file name and path of ack
    csv_buffer.seek(0)
    s3_client.upload_fileobj(csv_buffer, ack_bucket_name, f"ack/{ack_filename}.zip")

def lambda_handler(event, context):
    for record in event['Records']:
        errors =[]
        try:
            bucket_name = record['s3']['bucket']['name']
            file_key = record['s3']['object']['key']
            supplier = identify_supplier(file_key)
            disease_type = identify_disease_type(file_key)
            timestamp = identify_timestamp(file_key)
            
            # TO DO- Perform initial file validation
            validation_passed, validation_errors = initial_file_validation(file_key, bucket_name)
            errors.extend(validation_errors)
            
            if validation_passed:
                message_body = {
                    'disease_type': disease_type,
                    'supplier': supplier,
                    'timestamp': timestamp
                }
                send_to_supplier_queue(supplier, message_body)
            
            ack_bucket_name = 'immunisation-fhir-api-int-batch-data-destination'
            create_ack_file(bucket_name, file_key, ack_bucket_name, errors)
            
        #TO DO - errors to go to cloudwatch also
        except Exception as e:
            print(f"Error processing file")
            #errors.append(str(e))

    return {
        'statusCode': 200,
        'body': json.dumps('File processing completed')
    }
