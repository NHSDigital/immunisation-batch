"""
Lambda function for the fileprocessor lambda.
NOTE: The expected file format for the incoming file is 'VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv'.
e.g. 'Flu_Vaccinations_v5_YYY78_20240708T12130100.csv' (ODS code has multiple lengths)
"""

import json
from datetime import datetime
from typing import Union
import csv
import os
import logging
from io import BytesIO, StringIO
import uuid
import boto3
from constants import Constants
from fetch_permissions import get_permissions_config_json_from_s3


logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3_client = boto3.client("s3", region_name="eu-west-2")
sqs_client = boto3.client("sqs", region_name="eu-west-2")


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def get_csv_content_dict_reader(bucket_name: str, file_key: str):
    """Downloads the csv data and returns a csv_reader with the content of the csv"""
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = csv_obj["Body"].read().decode("utf-8")
    return csv.DictReader(StringIO(csv_content_string), delimiter="|")


def identify_supplier(ods_code: str) -> Union[str, None]:
    """Identify the supplier from the ods code using the mapping"""
    return Constants.ODS_TO_SUPPLIER_MAPPINGS.get(ods_code)


def is_valid_datetime(timestamp: str) -> bool:
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


def validate_content_headers(csv_content_reader):
    """Returns a bool to indicate whether the given CSV headers match the 34 expected headers exactly"""
    return csv_content_reader.fieldnames == Constants.EXPECTED_CSV_HEADERS


def extract_file_key_elements(file_key: str) -> dict:
    """Returns a dictionary containing each of the elements which can be extracted from the file key"""
    file_key_parts_without_extension = file_key.split(".")[0].split("_")
    return {
        "vaccine_type": file_key_parts_without_extension[0].upper(),
        "vaccination": file_key_parts_without_extension[1].lower(),
        "version": file_key_parts_without_extension[2].lower(),
        "ods_code": file_key_parts_without_extension[3],
        "timestamp": file_key_parts_without_extension[4],
        "extension": file_key.split(".")[1],
    }


def get_supplier_permissions(supplier: str) -> list:
    """
    Returns the permissions for the given supplier. Returns an empty list if the permissions config json could not
    be downloaded, or the supplier has no permissions.
    """
    config_bucket_name = os.getenv("CONFIG_BUCKET_NAME", f"immunisation-batch-{get_environment()}-config")
    return get_permissions_config_json_from_s3(config_bucket_name).get("all_permissions", {}).get(supplier, [])


def validate_vaccine_type_permissions(supplier: str, vaccine_type: str):
    """Returns True if the given supplier has any permissions for the given vaccine type, else False"""
    allowed_permissions = get_supplier_permissions(supplier)
    return vaccine_type in " ".join(allowed_permissions)


def validate_action_flag_permissions(csv_dict_reader, supplier: str, vaccine_type: str) -> bool:
    """
    Returns True if the supplier has permission to perform ANY of the requested actions for the given vaccine type,
    else False.
    """
    # Obtain the allowed permissions for the supplier
    allowed_permissions_set = set(get_supplier_permissions(supplier))

    # If the supplier has full permissions for the vaccine type return True
    if f"{vaccine_type}_FULL" in allowed_permissions_set:
        logger.info("%s has FULL permissions to create, update and delete", supplier)
        return True

    # Extract a list of all unique operation permissions requested in the csv file
    operations_requested = set()
    for row in csv_dict_reader:
        action_flag = row.get("ACTION_FLAG", "").upper()
        operations_requested.add("CREATE" if action_flag == "NEW" else action_flag)

    # Check if any of the CSV permissions match the allowed permissions
    operation_requests_set = {f"{vaccine_type}_{operation}" for operation in operations_requested}
    if operation_requests_set.intersection(allowed_permissions_set):
        logger.info(
            "%s permissions %s matches one of the requested permissions required to %s",
            supplier,
            allowed_permissions_set,
            operation_requests_set,
        )
        return True

    return False


def initial_file_validation(file_key: str, bucket_name: str) -> bool:
    """
    Return True if all elements of file key are valid, content headers are valid and the supplier has the
    appropriate permissions. Else return False.
    """
    # Validate file name format
    if not (file_key.endswith(".csv") and file_key.count("_") == 4):
        return False

    # Validate each part of the file name
    file_key_elements = extract_file_key_elements(file_key)
    supplier = identify_supplier(file_key_elements["ods_code"])
    vaccine_type = file_key_elements["vaccine_type"]
    if not (
        vaccine_type in Constants.VALID_VACCINE_TYPES
        and file_key_elements["vaccination"] == "vaccinations"
        and file_key_elements["version"] in Constants.VALID_VERSIONS
        and supplier  # Note that if supplier could be identified, this also verifies that ODS code is valid
        and is_valid_datetime(file_key_elements["timestamp"])
    ):
        logger.error("Invalid file key")
        return False

    # Obtain the file content
    csv_content_dict_reader = get_csv_content_dict_reader(bucket_name=bucket_name, file_key=file_key)

    # Validate the content headers
    if not validate_content_headers(csv_content_dict_reader):
        logger.error("Incorrect column headers")
        return False

    # Validate has permissions for the vaccine type
    if not validate_vaccine_type_permissions(supplier, vaccine_type):
        logger.error("%s does not have permissions for %s", supplier, vaccine_type)
        return False

    # Validate has permission to perform at least one of the requested actions
    if not validate_action_flag_permissions(csv_content_dict_reader, supplier, vaccine_type):
        logger.info("%s does not have permissions for any csv ACTION_FLAG operations", supplier)
        return False

    return True


def send_to_supplier_queue(supplier: str, message_body: dict) -> bool:
    """Sends a message to the supplier queue and returns a bool indicating if the message has been successfully sent"""
    # Find the URL of the relevant queue
    imms_env = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")
    sqs_name = Constants.SUPPLIER_TO_SQSQUEUE_MAPPINGS.get(supplier, supplier)
    account_id = os.getenv("PROD_ACCOUNT_ID") if "prod" in imms_env else os.getenv("LOCAL_ACCOUNT_ID")
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{account_id}/{imms_env}-{sqs_name}-metadata-queue.fifo"

    # Send to queue
    try:
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body), MessageGroupId="default")
        logger.info("Message sent to SQS queue '%s' for supplier %s", sqs_name, supplier)
    except sqs_client.exceptions.QueueDoesNotExist:
        logger.error("Failed to send messaage because queue %s does not exist", queue_url)
        return False
    return True


def create_ack_file(
    message_id: str,
    file_key: str,
    validation_passed: bool,
    message_delivery: bool,
    created_at_formatted,
) -> None:
    """Creates the ack file and uploads it to the S3 ack bucket"""
    ack_dict = {
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

    # Construct ack file
    ack_filename = f"ack/{file_key.split('.')[0]}_response.csv"

    # Create CSV file with | delimiter, filetype .csv
    csv_buffer = StringIO()
    csv_writer = csv.writer(csv_buffer, delimiter="|")
    csv_writer.writerow(list(ack_dict.keys()))
    csv_writer.writerow(list(ack_dict.values()))

    # Upload the CSV file to S3
    csv_buffer.seek(0)
    csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-destination")
    s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_filename)


def try_to_validate_file(file_key: str, bucket_name: str) -> bool:
    """Attempts initial file validation. Returns a bool to indicate if validation has been passed."""
    try:
        validation_passed = initial_file_validation(file_key, bucket_name)
    except ValueError as ve:
        logging.error("Error in initial_file_validation'%s': %s", file_key, str(ve))
        return False

    if not validation_passed:
        logging.error("Error in initial_file_validation")

    return validation_passed


def try_to_send_message(file_key: str, message_id: str) -> bool:
    """
    Attempts to send a message to the SQS queue.
    Returns a bool to indication if the message has been sent successfully.
    """
    file_key_elements = extract_file_key_elements(file_key)

    if not (supplier := identify_supplier(file_key_elements["ods_code"])):
        logger.error("Message not sent to supplier queue as unable to identify supplier")
        return False

    message_body = {
        "message_id": message_id,
        "vaccine_type": file_key_elements["vaccine_type"],
        "supplier": supplier,
        "timestamp": file_key_elements["timestamp"],
        "filename": file_key,
    }

    return send_to_supplier_queue(supplier, message_body)


def lambda_handler(event, context):
    """Lambda handler for filenameprocessor lambda"""
    error_files = []

    # For each file
    for record in event["Records"]:

        # Assign a unique message_id
        message_id = str(uuid.uuid4())

        # Obtain the file details
        bucket_name = record["s3"]["bucket"]["name"]
        file_key = record["s3"]["object"]["key"]
        response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        created_at_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

        try:
            # Validate the file
            validation_passed = try_to_validate_file(file_key, bucket_name)

            # If file is valid then send a message to the SQS queue
            if validation_passed:
                message_delivered = try_to_send_message(file_key, message_id)
            else:
                message_delivered = False

        except Exception as e:
            logging.error("Error processing file'%s': %s", file_key, str(e))
            validation_passed = False
            message_delivered = False
            error_files.append(file_key)

        create_ack_file(message_id, file_key, validation_passed, message_delivered, created_at_string)

    if error_files:
        logger.error("Processing errors occurred for the following files: %s", ", ".join(error_files))

    logger.info("Completed processing all file metadata in current batch")
    return {"statusCode": 200, "body": json.dumps("File processing for S3 bucket completed")}
