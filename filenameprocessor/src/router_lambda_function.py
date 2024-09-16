"""Lambda function for the fileprocessor lambda"""

import json
from datetime import datetime
import re
import csv
import os
import logging
from io import BytesIO, StringIO
import uuid
import boto3
from ods_patterns import ODS_PATTERNS, SUPPLIER_SQSQUEUE_MAPPINGS
from constants import Constant
from fetch_permissions import get_permissions_config_json_from_s3


# Incoming file format VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv
# for example: Flu_Vaccinations_v5_YYY78_20240708T12130100.csv - ODS code has multiple lengths
logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3_client = boto3.client("s3", region_name="eu-west-2")
sqs_client = boto3.client("sqs", region_name="eu-west-2")


def get_environment() -> str:
    """Returns the current environment"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user workspaces
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


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


def get_supplier_permissions(supplier: str, config_bucket_name: str) -> list:
    """
    Returns the permissions for the given supplier. Returns an empty list if the permissions config json could not
    be downloaded, or the supplier has no permissions.
    """
    # print(f"config_perms_check: {supplier_permissions}")
    # print(f"ALL_PERMISSIONS:{all_permissions}")
    return get_permissions_config_json_from_s3(config_bucket_name).get("all_permissions", {}).get(supplier, [])


def validate_vaccine_type_permissions(config_bucket_name: str, supplier: str, vaccine_type: str):
    """Returns True if the given supplier has any permissions for the given vaccine type, else False"""
    # print(f"BUCKET_NAME:{config_bucket_name}")
    # print(f"VACCINE TYPE 1:{vaccine_type}")
    # print(f"supplier:{supplier}")
    allowed_permissions = get_supplier_permissions(supplier, config_bucket_name)
    # print(f"Config Supplier Allowed Permissions: {allowed_permissions}")
    if (vaccine_type := vaccine_type.upper()) in " ".join(allowed_permissions):
        return True
    logger.error("Permission issue: %s does not have any permissions for %s", supplier, vaccine_type)
    return False


def validate_action_flag_permissions(
    bucket_name: str, file_key: str, supplier: str, vaccine_type: str, config_bucket_name: str
) -> bool:
    """
    Returns True if the supplier has permission to perform ANY of the requested actions for the given vaccine type,
    else False
    """
    allowed_permissions = get_supplier_permissions(supplier, config_bucket_name)
    # print(f"Allowed_permissions: {allowed_permissions}")

    # If the supplier has full permissions for the vaccine type return True
    if f"{vaccine_type.upper()}_FULL" in allowed_permissions:
        logger.info(f"{supplier} has FULL permissions to create, update and delete")
        # print(f"{supplier} has full permissions to create, update and delete")
        return True

    # Extract a list of all unique action flags in the csv file
    unique_action_flags = set()
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    body = csv_obj["Body"].read().decode("utf-8")
    csv_reader = csv.DictReader(StringIO(body), delimiter="|")
    for row in csv_reader:
        # print(f"ACTION FLAG {action_flag}")
        unique_action_flags.add(row.get("ACTION_FLAG", "").upper())
        # print(f"MAPPED PERMISSIONS {unique_permissions}")

    # Replace 'NEW' with 'CREATE'
    if "NEW" in unique_action_flags:
        unique_action_flags.remove("NEW")
        unique_action_flags.add("CREATE")

    # Check if any of the CSV permissions match the allowed permissions
    # print(f"CSV OPERATION REQUEST {csv_operation_request} AND UNIQUE PERMISSIONS {allowed_permissions_set}")
    if any(f"{vaccine_type.upper()}_{action_flag}" in allowed_permissions for action_flag in unique_action_flags):
        # print(
        #     f"{supplier} permission {allowed_permissions_set} matches "
        #     f"one of the csv operation permissions required to {csv_operation_request}"
        # )
        return True

    # print(f"supplier does not have required permissions {csv_operation_request}")
    return False


def extract_file_key_elements(file_key: str) -> dict:
    """Returns a dictionary containing each of the elements which can be extracted from the file key"""
    file_key_parts_without_extension = file_key.split(".")[0].split("_")
    return {
        "vaccine_type": file_key_parts_without_extension[0].lower(),
        "vaccination": file_key_parts_without_extension[1].lower(),
        "version": file_key_parts_without_extension[2].lower(),
        "ods_code": file_key_parts_without_extension[3],
        "timestamp": file_key_parts_without_extension[4],
        "extension": file_key.split(".")[1],
    }


def initial_file_validation(file_key, bucket_name):
    # Check if the file name ends with .csv
    if not (file_key.endswith(".csv") and file_key.count("_") == 4):
        return False

    # Validate each part of the file name
    elements = extract_file_key_elements(file_key)
    vaccine_type = elements["vaccine_type"]

    if not (
        vaccine_type in Constant.valid_vaccine_type
        and elements["vaccination"] == "vaccinations"
        and elements["version"] in Constant.valid_versions
        and any(re.match(pattern, elements["ods_code"]) for pattern in Constant.valid_ods_codes)
        and is_valid_datetime(elements["timestamp"])
    ):
        return False

    csv_content_reader = get_csv_content_reader(bucket_name=bucket_name, file_key=file_key)

    # Validate the content headers
    if not validate_content_headers(csv_content_reader):
        logger.error("Incorrect column headers")
        return False

    config_bucket_name = os.getenv("CONFIG_BUCKET_NAME", f"immunisation-batch-{get_environment()}-config")
    supplier = identify_supplier(elements["ods_code"])

    # Validate has permissions for the vaccine type
    if not validate_vaccine_type_permissions(config_bucket_name, supplier, vaccine_type):
        logger.info("%s does not have permissions for %s", supplier, vaccine_type)
        return False

    # Validate has permission to perform at least one of the requested actions
    if not validate_action_flag_permissions(bucket_name, file_key, supplier, vaccine_type, config_bucket_name):
        logger.info("%s does not have permissions for any csv ACTION_FLAG operations", supplier)
        return False

    return True


def get_csv_content_reader(bucket_name: str, file_key: str):
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_body = csv_obj["Body"].read().decode("utf-8")
    return csv.DictReader(StringIO(csv_body), delimiter="|")


def validate_content_headers(csv_content_reader):
    """Returns a bool to indicate whether the given CSV headers match the 34 expected headers exactly"""
    return csv_content_reader.fieldnames == Constant.expected_csv_headers


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


def create_ack_file(message_id, file_key, ack_bucket_name, validation_passed, message_delivery, created_at_formatted):
    ack = {
        "MESSAGE_HEADER_ID": message_id,
        "HEADER_RESPONSE_CODE": "Success" if validation_passed else "Failure",
        "ISSUE_SEVERITY": "Information" if validation_passed else "Fatal",
        "ISSUE_CODE": "OK" if validation_passed else "Fatal Error",
        "ISSUE_DETAILS_CODE": "20013" if validation_passed else "10001",
        "RESPONSE_TYPE": "Technical",
        "RESPONSE_CODE": "20013" if validation_passed else "10002",
        "RESPONSE_DISPLAY": (
            "Success" if validation_passed else "Infrastructure Level Response Value - Processing Error"
        ),
        "RECEIVED_TIME": created_at_formatted,
        "MAILBOX_FROM": "TBC",  # TODO: Use correct value once known
        "LOCAL_ID": "TBC",  # TODO: Use correct value once known
        "MESSAGE_DELIVERY": message_delivery,
    }
    # construct acknowlegement file
    ack_filename = f"ack/{file_key.split('.')[0]}_response.csv"
    print(f"{list(ack.values())}")
    # Create CSV file with | delimiter, filetype .csv
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, delimiter="|")
    csv_writer.writerow(list(ack.keys()))
    csv_writer.writerow(list(ack.values()))

    # Upload the CSV file to S3
    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)


def lambda_handler(event, context):
    error_files = []
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-destination")

    for record in event["Records"]:
        bucket_name = record["s3"]["bucket"]["name"]
        file_key = record["s3"]["object"]["key"]
        message_id = str(uuid.uuid4())
        response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        created_at_formatted = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

        # Default validation_passed and message_delivery to False
        validation_passed = False
        message_delivered = False

        try:
            try:
                validation_passed = initial_file_validation(file_key, bucket_name)
            except ValueError as ve:
                logging.error("Error in initial_file_validation'%s': %s", file_key, str(ve))

            if not validation_passed:
                logging.error("Error in initial_file_validation")

            if validation_passed and (supplier := identify_supplier(extract_ods_code(file_key))):

                message_body = {
                    "message_id": message_id,
                    "vaccine_type": identify_vaccine_type(file_key),
                    "supplier": supplier,
                    "timestamp": identify_timestamp(file_key),
                    "filename": file_key,
                }
                if send_to_supplier_queue(supplier, message_body):
                    logger.info("File added to SQS queue for %s pipeline", supplier)
                    message_delivered = True
                else:
                    logger.error("Failed to send file to %s_pipeline", supplier)

        except Exception as e:
            logging.error("Error processing file'%s': %s", file_key, str(e))
            validation_passed = False
            error_files.append(file_key)
        create_ack_file(
            message_id, file_key, ack_bucket_name, validation_passed, message_delivered, created_at_formatted
        )

    if error_files:
        logger.error("Processing errors occurred for the following files: %s", ", ".join(error_files))

    logger.info("Completed processing all file metadata in current batch")
    return {"statusCode": 200, "body": json.dumps("File processing for S3 bucket completed")}


def is_valid_datetime(timestamp):
    """
    Returns a bool to indicate whether the timestamp is a valid datetime in the format 'YYYYmmddTHHMMSSzz'
    where 'zz' is a two digit number indicating the timezone
    """

    # Timezone is represented by the final two digits
    if not (timezone := timestamp[-2:]).isdigit() or int(timezone) < 0 or int(timezone) > 23:
        return False

    # Check that datetime (excluding timezone) is a valid datetime in the expected format
    try:
        datetime.strptime(timestamp[:-2], "%Y%m%dT%H%M%S")
    except ValueError:
        return False

    return True
