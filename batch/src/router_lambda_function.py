
import json
import boto3
import re
import csv
import os
import logging
from io import BytesIO, StringIO
from ods_patterns import ODS_PATTERNS
from datetime import datetime

# Incoming file format DISEASETYPE_Vaccinations_version_ODSCODE_DATETIME.csv
# for example: Flu_Vaccinations_v5_YYY78_20240708T12130100.csv - ODS code has multiple lengths


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3', region_name='eu-west-2')
sqs_client = boto3.client('sqs', region_name='eu-west-2')


def get_environment():
    _env = os.getenv("ENVIRONMENT", "internal-dev")
    non_prod = ["internal-dev", "int", "ref", "sandbox"]
    if _env in non_prod:
        return _env
    elif _env == "prod":
        return "prod"
    else:
        return "internal-dev"  # default to internal-dev for pr and user workspaces


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
    # Define valid values
    valid_disease_types = ["FLU", "COVID19", "MMR", "Flu", "Covid19", "Mmr", "flu", "covid19", "mmr"]
    valid_versions = ["v5"]
    valid_ods_codes = ["YGM41", "8J1100001", "8HK48", "YGA", "0DE", "0DF", "8HA94", "X26"]

    # Check if the file name ends with .csv
    if not file_key.endswith('.csv'):
        return False, True

    # Check the structure of the file name
    parts = file_key.split('_')
    if len(parts) != 5:
        return False, True

    # Validate each part of the file name
    disease_type = parts[0]
    vaccination = parts[1]
    version = parts[2]
    ods_code = parts[3]
    timestamp = parts[4].split('.')[0]

    if disease_type not in valid_disease_types:
        return False, True

    if vaccination != "Vaccinations":
        return False, True

    if version not in valid_versions:
        return False, True

    if not any(re.match(pattern, ods_code) for pattern in valid_ods_codes):
        return False, True

    if not re.match(r'\d{8}T\d{6}', timestamp) or not is_valid_datetime(timestamp):
        return False, True

    column_count_valid, column_count_errors = validate_csv_column_count(bucket_name, file_key)
    if not column_count_valid:
        return False, True

    return True, False


def send_to_supplier_queue(supplier, message_body):
    # Need to confirm supplier queue name format
    imms_env = get_environment()
    ACCOUNT_ID = os.getenv(f"{imms_env.upper()}_ACCOUNT_ID")
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{ACCOUNT_ID}/{supplier}_queue"
    sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
    print(f"{queue_url}")


def create_ack_file(file_key, ack_bucket_name, validation_passed):
    # TO DO - Populate acknowledgement file with correct values once known
    headers = ['MESSAGE_HEADER_ID', 'HEADER_RESPONSE_CODE', 'ISSUE_SEVERITY', 'ISSUE_CODE', 'RESPONSE_TYPE',
               'RESPONSE_CODE', 'RESPONSE_DISPLAY', 'RECEIVED_TIME', 'MAILBOX_FROM', 'LOCAL_ID']

    # Placeholder for data rows for success
    if validation_passed:
        data_rows = [['Value1', 'Value2', 'Value3', 'Value4', 'Value5',
                     'Value6', 'Value7', 'Value8', 'Value9', 'Value10']]
        ack_filename = (f"GP_Vaccinations_Processing_Response_v1_0_{extract_ods_code(file_key)}"
                        f"_{identify_timestamp(file_key)}.csv")
    # Placeholder for data rows for errors
    else:
        data_rows = [
            ['TBC', 'fatal-error', 'error', 'error', 'business',
             '20005', 'Unsupported file type received as an attachment', identify_timestamp(file_key), 'N/A', 'DPS']]
        # construct acknowlegement file
        ack_filename = (f"GP_Vaccinations_Processing_Response_v1_0_{extract_ods_code(file_key)}"
                        f"_{identify_timestamp(file_key)}.csv")
        print(f"{data_rows}")
    # Create CSV file with | delimiter, filetype .csv
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, delimiter='|')
    csv_writer.writerow(headers)
    csv_writer.writerows(data_rows)

    # Upload the CSV.zip file to S3
    # TO DO - Update file name and path of ack, Is it nested in a directory in the S3 bucket?
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
            imms_env = get_environment()
            ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f'immunisation-fhir-api-{imms_env}-batch-data-destination')

            # Create acknowledgment file
            # create_ack_file(bucket_name, file_key, ack_bucket_name, validation_passed, validation_errors)

            # if validation passed, send message to SQS queue
            if validation_passed and supplier:
                create_ack_file(file_key, ack_bucket_name, True)
                message_body = {
                    'disease_type': disease_type,
                    'supplier': supplier,
                    'timestamp': timestamp
                }
                send_to_supplier_queue(supplier, message_body)
                logger.info(f"Message sent to SQS queue for supplier {supplier}")
            elif not supplier:
                # if supplier not found or ods_code does not exist , log error, no sqs message
                logging.error(f" Supplier not found for ods code {ods_code}")
            else:
                logging.error("Error in initial_file_validation")
                create_ack_file(file_key, ack_bucket_name, False)

        # Error handling for file processing
        except ValueError as ve:
            logging.error(f"Error in initial_file_validation'{file_key}': {str(ve)}")
            create_ack_file(bucket_name, file_key, ack_bucket_name, False, [str(ve)])

        except Exception as e:
            logging.error(f"Error processing file'{file_key}': {str(e)}")
            create_ack_file(bucket_name, file_key, ack_bucket_name, False)
    return {
        'statusCode': 200,
        'body': json.dumps('File processing for S3 bucket completed')
    }


def is_valid_datetime(timestamp):

    # Extract date and time components
    date_part = timestamp[:8]
    time_part = timestamp[9:]

    # Validate date part
    # date_obj = datetime.strptime(date_part, '%Y%m%d')

    # Validate time part
    if len(time_part) != 8 or not time_part.isdigit():
        False
    hours = int(time_part[:2])
    minutes = int(time_part[2:4])
    seconds = int(time_part[4:6])

    # Check if time is valid
    if not (0 <= hours < 24 and 0 <= minutes < 60 and 0 <= seconds < 60):
        return False
    # Construct the valid datetime string
    valid_datetime_string = f"{date_part}T{time_part[:6]}"
    datetime_obj = datetime.strptime(valid_datetime_string, '%Y%m%dT%H%M%S')

    if not datetime_obj:
        return False

    return True


def validate_csv_column_count(bucket_name, file_key):
    expected_columns = [
        'NHS_NUMBER', 'PERSON_FORENAME', 'PERSON_SURNAME', 'PERSON_DOB', 'PERSON_GENDER_CODE', 'PERSON_POSTCODE',
        'DATE_AND_TIME', 'SITE_CODE', 'SITE_CODE_TYPE_URI', 'UNIQUE_ID', 'UNIQUE_ID_URI', 'ACTION_FLAG',
        'PERFORMING_PROFESSIONAL_FORENAME', 'PERFORMING_PROFESSIONAL_SURNAME', 'RECORDED_DATE', 'PRIMARY_SOURCE',
        'VACCINATION_PROCEDURE_CODE', 'VACCINATION_PROCEDURE_TERM', 'DOSE_SEQUENCE', 'VACCINE_PRODUCT_CODE',
        'VACCINE_PRODUCT_TERM', 'VACCINE_MANUFACTURER', 'BATCH_NUMBER', 'EXPIRY_DATE', 'SITE_OF_VACCINATION_CODE',
        'SITE_OF_VACCINATION_TERM', 'ROUTE_OF_VACCINATION_CODE', 'ROUTE_OF_VACCINATION_TERM', 'DOSE_AMOUNT',
        'DOSE_UNIT_CODE', 'DOSE_UNIT_TERM', 'INDICATION_CODE', 'LOCATION_CODE', 'LOCATION_CODE_TYPE_URI'
    ]

    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    body = csv_obj['Body'].read().decode('utf-8')
    csv_reader = csv.reader(StringIO(body))
    header = next(csv_reader)

    if len(header) != 34:
        return False, True

    if header != expected_columns:
        return False, True

    return True, False
