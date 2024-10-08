import csv
import json
from io import StringIO
import io
import os
from convert_fhir_json import convert_to_fhir_json
from get_imms_id import ImmunizationApi
import logging
from ods_patterns import SUPPLIER_SQSQUEUE_MAPPINGS
from botocore.exceptions import ClientError
from constants import Constants
from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
from utils_for_recordprocessor import get_environment
from get_action_flag_permissions import get_action_flag_permissions
from s3_clients import s3_client, kinesis_client


logging.basicConfig(level="INFO")
logger = logging.getLogger()
cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


def create_ack_data(created_at_formatted, message_header, delivered, diagnostics=None):
    """Returns a dictionary containing the ack headers as keys, along with the relevant values."""
    return {
        "MESSAGE_HEADER_ID": message_header,
        "HEADER_RESPONSE_CODE": "fatal-error" if diagnostics else "ok",
        "ISSUE_SEVERITY": "error" if diagnostics else "information",
        "ISSUE_CODE": "error" if diagnostics else "informational",
        "RESPONSE_TYPE": "business",
        "RESPONSE_CODE": "20005" if diagnostics else "20013",
        "RESPONSE_DISPLAY": diagnostics if diagnostics else "Success",
        "RECEIVED_TIME": created_at_formatted,
        "MAILBOX_FROM": "TBC",
        "LOCAL_ID": "DPS",
        "MESSAGE_DELIVERY": delivered,
    }


def send_to_kinesis(supplier, message_body):
    """Send a message to the specified Kinesis stream."""
    stream_name = SUPPLIER_SQSQUEUE_MAPPINGS.get(supplier, supplier)
    kinesis_queue_prefix = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")

    try:
        resp = kinesis_client.put_record(
            StreamName=f"{kinesis_queue_prefix}-processingdata-stream",
            StreamARN=os.getenv("KINESIS_STREAM_ARN"),
            Data=json.dumps(message_body, ensure_ascii=False),
            PartitionKey=supplier,
        )
        logger.info("Message sent to Kinesis stream:%s for supplier:%s with resp:%s", stream_name, supplier, resp)
    except ClientError as error:
        logger.error("Error sending message to Kinesis: %s", error)
        return False

    return True


def fetch_file_from_s3(bucket_name, file_key):
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_data = response["Body"].read().decode("utf-8")
    return csv.DictReader(StringIO(csv_data), delimiter="|")


def add_row_to_ack_file(ack_data, accumulated_ack_file_content, file_key):
    data_row_str = [str(item) for item in ack_data.values()]
    cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
    accumulated_ack_file_content.write(cleaned_row + "\n")
    csv_file_like_object = io.BytesIO(accumulated_ack_file_content.getvalue().encode("utf-8"))
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-destinations")
    ack_filename = f"processedFile/{file_key.replace('.csv', '_response.csv')}"
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
    logger.info(f"CSV content before upload with perms:\n{accumulated_ack_file_content.getvalue()}")
    return accumulated_ack_file_content


def process_row(vaccine_type, permission_operations, row):
    action_flag = action_flag.upper() if (action_flag := row.get("ACTION_FLAG")) is not None else ""
    logger.info(f"ACTION FLAG PERMISSION REQUESTED:  {action_flag}")
    logger.info(f"PERMISSIONS OPERATIONS {permission_operations}")

    # Handle no permissions
    if not (action_flag in permission_operations):
        logger.info(f"Skipping row as supplier does not have the permissions for this csv operation {action_flag}")

        return {
            "fhir_json": "No_Permissions",
            "action_flag": "No_Permissions",
            "imms_id": None,
            "version": None,
            "diagnostics": "No permissions for operation",
        }

    fhir_json, valid = convert_to_fhir_json(row, vaccine_type)

    # Handle missing UNIQUE_ID or UNIQUE_ID_URI or invalid conversion
    if not ((identifier_system := row.get("UNIQUE_ID_URI")) and (identifier_value := row.get("UNIQUE_ID")) and valid):
        logger.error("Invalid row format: row is missing either UNIQUE_ID or UNIQUE_ID_URI")
        return {
            "fhir_json": "None",
            "action_flag": "None",
            "imms_id": "None",
            "version": "None",
            "diagnostics": "Unsupported file type received as an attachment",
        }

    # Obtain the imms id and version from the ieds for update and delete
    if action_flag in ("DELETE", "UPDATE"):
        response, status_code = immunization_api_instance.get_imms_id(identifier_system, identifier_value)
        # Handle non-200 response from Immunisation API
        if not (response.get("total") == 1 and status_code == 200):
            logger.info("imms_id not found:%s and status_code: %s", response, status_code)
            return {
                "fhir_json": fhir_json,
                "action_flag": "None",
                "imms_id": "None",
                "version": "None",
                "diagnostics": "Unsupported file type received as an attachment",
            }

    # Handle success
    resource = response.get("entry", [])[0]["resource"] if action_flag in ("DELETE", "UPDATE") else None
    return {
        "fhir_json": fhir_json,
        "action_flag": action_flag,
        "imms_id": resource.get("id") if resource else None,
        "version": resource.get("meta", {}).get("versionId") if resource else None,
        "diagnostics": None,
    }


def process_csv_to_fhir(incoming_message_body):
    """
    For each row of the csv, attempts to transform into FHIR format, sends a message to kinesis,
    and documents the outcome for each row in the ack file.
    """

    logger.info("Event: %s", incoming_message_body)

    # Get details needed to process file
    file_id = incoming_message_body.get("message_id")
    vaccine_type = incoming_message_body.get("vaccine_type").upper()
    supplier = incoming_message_body.get("supplier").upper()
    file_key = incoming_message_body.get("filename")
    print("HERE1")
    action_flag_permissions = get_action_flag_permissions(supplier, vaccine_type)
    print("HERE2")

    # Fetch the data
    bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-sources")
    csv_reader = fetch_file_from_s3(bucket_name, file_key)

    # Initialise the accumulated_ack_file_content with the headers
    accumulated_ack_file_content = StringIO()  # Initialize a variable to accumulate CSV content
    accumulated_ack_file_content.write("|".join(Constants.ack_headers) + "\n")  # Write the header once at the start

    row_count = 0  # Initialize a counter for rows

    for row in csv_reader:
        row_count += 1
        message_id = f"{file_id}#{row_count}"
        logger.info("MESSAGE ID : %s", message_id)
        # Process the row to obtain the details needed for the message_body and ack file
        details_from_processing = process_row(vaccine_type, action_flag_permissions, row)
        # Create the message body for sending
        outgoing_message_body = {
            "message_id": message_id,
            "fhir_json": details_from_processing["fhir_json"],
            "action_flag": details_from_processing["action_flag"],
            "file_name": file_key,
        }
        if imms_id := details_from_processing.get("imms_id"):
            outgoing_message_body["imms_id"] = imms_id
        if version := details_from_processing.get("version"):
            outgoing_message_body["version"] = version

        # Send to kinesis. Add diagnostics if send fails.
        message_delivered = send_to_kinesis(supplier, outgoing_message_body)
        if (diagnostics := details_from_processing["diagnostics"]) is None and message_delivered is False:
            diagnostics = "Unsupported file type received as an attachment"

        # Update the ack file
        response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")
        ack_data_row = create_ack_data(created_at_formatted_string, message_id, message_delivered, diagnostics)
        accumulated_ack_file_content = add_row_to_ack_file(ack_data_row, accumulated_ack_file_content, file_key)

    logger.info("Total rows processed: %s", row_count)


def main(event):
    """Process each row of the file"""
    logger.info("task started")
    try:
        process_csv_to_fhir(incoming_message_body=json.loads(event))
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing message: %s", error)


if __name__ == "__main__":
    main(event=os.environ.get("EVENT_DETAILS"))
