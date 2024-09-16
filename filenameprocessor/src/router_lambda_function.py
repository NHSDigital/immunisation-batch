import json
from datetime import datetime
import re
import csv
import os
import logging
from io import BytesIO, StringIO
import boto3
from ods_patterns import ODS_PATTERNS, SUPPLIER_SQSQUEUE_MAPPINGS
from constants import Constant
from fetch_permissions import get_json_from_s3
import uuid


# Incoming file format VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv
# for example: Flu_Vaccinations_v5_YYY78_20240708T12130100.csv - ODS code has multiple lengths
logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3_client = boto3.client("s3", region_name="eu-west-2")
sqs_client = boto3.client("sqs", region_name="eu-west-2")


def get_environment():
    _env = os.getenv("ENVIRONMENT")
    non_prod = ["internal-dev", "int", "ref", "sandbox"]
    if _env in non_prod:
        return _env
    elif _env == "prod":
        return "prod"
    else:
        return "internal-dev"  # default to internal-dev for pr and user workspaces


def extract_ods_code(file_key):
    supplier_match = re.search(r"_Vaccinations_v\d+_(\w+)_\d+T\d+\.csv$", file_key)
    return supplier_match.group(1).upper() if supplier_match else None


def identify_supplier(ods_code):
    return ODS_PATTERNS.get(ods_code, None)


def identify_vaccine_type(file_key):
    vaccine_match = re.search(r"^(\w+)_Vaccinations_", file_key)
    return vaccine_match.group(1) if vaccine_match else None


def identify_timestamp(file_key):
    timestamp_match = re.search(r"_(\d+T\d+)\.csv$", file_key)
    return timestamp_match.group(1) if timestamp_match else None


def get_supplier_permissions(supplier, config_bucket_name):
    supplier_permissions = get_json_from_s3(config_bucket_name)
    print(f"config_perms_check: {supplier_permissions}")
    if supplier_permissions is None:
        return []
    all_permissions = supplier_permissions.get("all_permissions", {})
    print(f"ALL_PERMISSIONS:{all_permissions}")
    return all_permissions.get(supplier, [])


def validate_vaccine_type_permissions(config_bucket_name, supplier, vaccine_type):
    """Checks for permissions for vaccine type"""
    vaccine_type = vaccine_type.upper()
    print(f"BUCKET_NAME:{config_bucket_name}")
    print(f"VACCINE TYPE 1:{vaccine_type}")
    print(f"supplier:{supplier}")
    allowed_permissions = get_supplier_permissions(supplier, config_bucket_name)
    print(f"config_check: {allowed_permissions}")
    for permissions in allowed_permissions:
        if vaccine_type.upper() in permissions:
            # if permissions.startswith(vaccine_type):
            return True
    logger.error(f"vaccine type permission issue {vaccine_type}")
    return False


def validate_action_flag_permissions(
    bucket_name, file_key, supplier, vaccine_type, config_bucket_name
):
    """Checks if the ACTION_FLAG values in the CSV match any of the allowed permissions for the specific vaccine type"""
    # TO DO - COMPLETE SUPPLIER PERMISSION CHECKS

    # Fetch the CSV file from S3
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    body = csv_obj["Body"].read().decode("utf-8")

    # Read the CSV data
    csv_reader = csv.DictReader(StringIO(body), delimiter="|")

    # Store unique permissions from the CSV
    unique_permissions = set()

    # Iterate over each row to collect unique permissions
    for row in csv_reader:
        print(f"rowvalue:{row}")
        # Extract and process the ACTION_FLAG column
        action_flag = row.get("ACTION_FLAG", "")

        if action_flag is None:
            action_flag = ""
        action_flag = action_flag.split("|") if action_flag else []
        action_flag = [value.strip('"') if value else "" for value in action_flag]

        for flag in action_flag:
            flag = "CREATE" if flag == "new" else flag.upper()
            if flag:
                unique_permissions.add(flag)
                # print(f"MAPPED PERMISSIONS {unique_permissions}")
    # Get the allowed permissions for the supplier
    allowed_permissions = get_supplier_permissions(supplier, config_bucket_name)
    allowed_permissions_set = set(allowed_permissions)
    print(f"Allowed_permissionsP: {allowed_permissions}")
    # Check if the supplier has full permissions for the vaccine type
    if f"{vaccine_type.upper()}_FULL" in allowed_permissions_set:
        logger.info(f"{supplier} has FULL permissions to create, update and delete")
        print(f"{supplier} has full permissions to create, update and delete")
        return True

    # Check if any of the CSV permissions match the allowed permissions
    csv_operation_request = {
        f"{vaccine_type.upper()}_{perm.upper()}" for perm in unique_permissions
    }
    print(f"{csv_operation_request}")
    if csv_operation_request.intersection(allowed_permissions_set):
        logger.info(
            f"{supplier} permission {allowed_permissions_set} matches "
            f"one of the csv operation permissions required to {csv_operation_request}"
        )
        return True
    print(f"supplier does not have required permissions {csv_operation_request}")
    return False


def initial_file_validation(file_key, bucket_name):

    # Check if the file name ends with .csv
    if not file_key.endswith(".csv"):
        return False

    # Check the structure of the file name
    parts = file_key.split("_")
    if len(parts) != 5:
        return False

    # Validate each part of the file name
    vaccine_type = parts[0].lower()
    vaccination = parts[1].lower()
    version = parts[2].lower()
    ods_code = parts[3]
    timestamp = parts[4].split(".")[0]
    supplier = identify_supplier(ods_code)
    imms_env = get_environment()
    config_bucket_name = os.getenv(
        "CONFIG_BUCKET_NAME",
        f"immunisation-batch-{imms_env}-config",
    )

    if vaccine_type not in Constant.valid_vaccine_type:
        return False

    if vaccination != "vaccinations":
        return False

    if version not in Constant.valid_versions:
        return False

    if not any(re.match(pattern, ods_code) for pattern in Constant.valid_ods_codes):
        return False

    if not re.match(r"\d{8}T\d{6}", timestamp) or not is_valid_datetime(timestamp):
        return False

    column_count_valid = validate_csv_column_count(bucket_name, file_key)
    if not column_count_valid:
        logger.error(f"column count issue {supplier}")
        return False

    # Validate if has the vaccine_type permissions
    if not validate_vaccine_type_permissions(
        config_bucket_name, supplier, vaccine_type
    ):
        logger.error(f"vaccine type permissions issue {supplier}")
        return False

    # Validate the ACTION_FLAG column for permissions - if none reject
    if not validate_action_flag_permissions(
        bucket_name, file_key, supplier, vaccine_type, config_bucket_name
    ):
        logger.error(f"action flag permission issue {supplier}")
        return False

    return True


def send_to_supplier_queue(supplier, message_body):
    # Send a message to the supplier queue
    imms_env = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")
    SQS_name = SUPPLIER_SQSQUEUE_MAPPINGS.get(supplier, supplier)
    if "prod" in imms_env or "production" in imms_env:
        account_id = os.getenv("PROD_ACCOUNT_ID")
    else:
        account_id = os.getenv("LOCAL_ACCOUNT_ID")
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{account_id}/{imms_env}-{SQS_name}-metadata-queue.fifo"
    print(f"Queue_URL: {queue_url}")

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


def create_ack_file(
    message_id, file_key, ack_bucket_name, validation_passed, message_delivery, created_at_formatted
):
    # TO DO - Populate acknowledgement file with correct values once known
    headers = [
        "MESSAGE_HEADER_ID",
        "HEADER_RESPONSE_CODE",
        "ISSUE_SEVERITY",
        "ISSUE_CODE",
        "RESPONSE_TYPE",
        "RESPONSE_CODE",
        "RESPONSE_DISPLAY",
        "RECEIVED_TIME",
        "MAILBOX_FROM",
        "LOCAL_ID",
        "MESSAGE_DELIVERY",
    ]
    parts = file_key.split(".")
    # Placeholder for data rows for success
    if validation_passed:
        data_rows = [
            [
                message_id,
                "ok",
                "information",
                "informational",
                "business",
                "20013",
                "Success",
                created_at_formatted,
                "TBC",
                "DPS",
                message_delivery,
            ]
        ]
        ack_filename = f"ack/{parts[0]}_response.csv"
    # Placeholder for data rows for errors
    else:
        data_rows = [
            [
                message_id,
                "fatal-error",
                "error",
                "error",
                "business",
                "20005",
                "Unsupported file type received as an attachment",
                created_at_formatted,
                "TBC",
                "DPS",
                message_delivery,
            ]
        ]
        # construct acknowlegement file
        ack_filename = f"ack/{parts[0]}_response.csv"
        print(f"{data_rows}")
    # Create CSV file with | delimiter, filetype .csv
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, delimiter="|")
    csv_writer.writerow(headers)
    csv_writer.writerows(data_rows)

    # Upload the CSV file to S3
    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)


def lambda_handler(event, context):
    error_files = []
    # Determine ack_bucket_name based on environment
    imms_env = get_environment()
    ack_bucket_name = os.getenv(
        "ACK_BUCKET_NAME",
        f"immunisation-batch-{imms_env}-data-destination",
    )

    for record in event["Records"]:
        try:
            bucket_name = record["s3"]["bucket"]["name"]
            file_key = record["s3"]["object"]["key"]
            message_id = str(uuid.uuid4())
            # Initial file validation
            response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
            created_at = response["LastModified"]
            created_at_formatted = created_at.strftime("%Y%m%dT%H%M%S00")

            validation_passed = initial_file_validation(file_key, bucket_name)

            if not validation_passed:
                logging.error("Error in initial_file_validation")
                create_ack_file(
                    message_id, file_key, ack_bucket_name, False, False, created_at_formatted
                )

            ods_code = extract_ods_code(file_key)
            vaccine_type = identify_vaccine_type(file_key)
            timestamp = identify_timestamp(file_key)
            supplier = identify_supplier(ods_code)

            # if validation passed, send message to SQS queue
            if validation_passed and supplier:

                message_body = {
                    "message_id": message_id,
                    "vaccine_type": vaccine_type,
                    "supplier": supplier,
                    "timestamp": timestamp,
                    "filename": file_key,
                }
                status = send_to_supplier_queue(supplier, message_body)
                if status:
                    logger.info(f"File added to SQS queue for {supplier} pipeline")
                    create_ack_file(
                        message_id, file_key, ack_bucket_name, True, True, created_at_formatted
                    )
                else:
                    logger.error(f"Failed to send file to {supplier}_pipeline")
                    create_ack_file(
                        message_id, file_key, ack_bucket_name, True, False, created_at_formatted
                    )

        # Error handling for file processing
        except ValueError as ve:
            logging.error(f"Error in initial_file_validation'{file_key}': {str(ve)}")
            create_ack_file(
                message_id, file_key, ack_bucket_name, False, False, created_at_formatted
            )
        except Exception as e:
            logging.error(f"Error processing file'{file_key}': {str(e)}")
            create_ack_file(
                message_id, file_key, ack_bucket_name, False, False, created_at_formatted
            )
            error_files.append(file_key)
    if error_files:
        logger.error(
            f"Processing errors occurred for the following files: {', '.join(error_files)}"
        )

    logger.info("Completed processing all file metadata in current batch")
    return {
        "statusCode": 200,
        "body": json.dumps("File processing for S3 bucket completed"),
    }


def is_valid_datetime(timestamp):

    # Extract date and time component
    date_part = timestamp[:8]
    time_part = timestamp[9:]

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

    datetime_obj = datetime.strptime(valid_datetime_string, "%Y%m%dT%H%M%S")

    if not datetime_obj:
        return False

    return True


def validate_csv_column_count(bucket_name, file_key):
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    body = csv_obj["Body"].read().decode("utf-8")
    csv_reader = csv.reader(StringIO(body))
    header = next(csv_reader)[0].split("|")

    if len(header) != 34:
        return False

    for item in header:
        if item not in Constant.expected_csv_content:
            return False

    return True
