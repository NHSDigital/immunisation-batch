"""Functions for processing the file on a row-by-row basis"""

import json
from io import StringIO
import os
import time
import logging
from constants import Constants
from utils_for_recordprocessor import get_environment, get_csv_content_dict_reader
from unique_permission import get_unique_action_flags_from_s3
from make_and_upload_ack_file import make_and_upload_ack_file
from get_operation_permissions import get_operation_permissions
from process_row import process_row
from mappings import Vaccine
from update_ack_file import update_ack_file
from send_to_kinesis import send_to_kinesis
from s3_clients import s3_client


logging.basicConfig(level="INFO")
logger = logging.getLogger()


def process_csv_to_fhir(incoming_message_body: dict) -> None:
    """
    For each row of the csv, attempts to transform into FHIR format, sends a message to kinesis,
    and documents the outcome for each row in the ack file.
    """
    logger.info("Event: %s", incoming_message_body)

    # Get details needed to process file
    file_id = incoming_message_body.get("message_id")
    vaccine: Vaccine = next(  # Convert vaccine_type to Vaccine enum
        vaccine
        for vaccine in Vaccine
        if vaccine.value == incoming_message_body.get("vaccine_type").upper()
    )
    supplier = incoming_message_body.get("supplier").upper()
    file_key = incoming_message_body.get("filename")
    permission = incoming_message_body.get("permission")
    allowed_operations = get_operation_permissions(vaccine, permission)

    # Fetch the data
    bucket_name = os.getenv(
        "SOURCE_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-sources"
    )
    csv_reader = get_csv_content_dict_reader(bucket_name, file_key)

    is_valid_headers = validate_content_headers(csv_reader)
    # Validate has permission to perform at least one of the requested actions
    action_flag_check = validate_action_flag_permissions(
        bucket_name, file_key, supplier, vaccine.value, permission
    )

    if not action_flag_check or not is_valid_headers:
        print("failed")
        response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        created_at_formatted_string = response["LastModified"].strftime(
            "%Y%m%dT%H%M%S00"
        )
        make_and_upload_ack_file(file_id, file_key, created_at_formatted_string)
    else:
        # Initialise the accumulated_ack_file_content with the headers
        accumulated_ack_file_content = StringIO()
        accumulated_ack_file_content.write("|".join(Constants.ack_headers) + "\n")

        row_count = 0  # Initialize a counter for rows
        for row in csv_reader:
            row_count += 1
            row_id = f"{file_id}#{row_count}"
            logger.info("MESSAGE ID : %s", row_id)
            # Process the row to obtain the details needed for the message_body and ack file
            details_from_processing = process_row(vaccine, allowed_operations, row)

            # Create the message body for sending
            outgoing_message_body = {
                "row_id": row_id,
                "file_key": file_key,
                "supplier": supplier,
                **details_from_processing,
            }

            # Send to kinesis. Add diagnostics if send fails.
            message_delivered = send_to_kinesis(supplier, outgoing_message_body)
            if (
                diagnostics := details_from_processing.get("diagnostics")
            ) is None and message_delivered is False:
                diagnostics = "Unsupported file type received as an attachment"

            # Update the ack file
            accumulated_ack_file_content = update_ack_file(
                file_key,
                bucket_name,
                accumulated_ack_file_content,
                row_id,
                message_delivered,
                diagnostics,
                outgoing_message_body.get("imms_id"),
            )

        logger.info("Total rows processed: %s", row_count)


def validate_content_headers(csv_content_reader):
    """Returns a bool to indicate whether the given CSV headers match the 34 expected headers exactly"""
    return csv_content_reader.fieldnames == Constants.expected_csv_headers


def validate_action_flag_permissions(
    bucket_name, key, supplier: str, vaccine_type: str, permission
) -> bool:
    """
    Returns True if the supplier has permission to perform ANY of the requested actions for the given vaccine type,
    else False.
    """
    # Obtain the allowed permissions for the supplier
    allowed_permissions_set = permission
    # If the supplier has full permissions for the vaccine type, return True
    if f"{vaccine_type}_FULL" in allowed_permissions_set:
        return True

    # Get unique ACTION_FLAG values from the S3 file
    operations_requested = get_unique_action_flags_from_s3(bucket_name, key)

    # Convert action flags into the expected operation names
    operation_requests_set = {
        f"{vaccine_type}_{'CREATE' if action == 'NEW' else action}"
        for action in operations_requested
    }

    # Check if any of the CSV permissions match the allowed permissions
    if operation_requests_set.intersection(allowed_permissions_set):
        logger.info(
            "%s permissions %s match one of the requested permissions required to %s",
            supplier,
            allowed_permissions_set,
            operation_requests_set,
        )
        return True

    return False


def main(event: str) -> None:
    """Process each row of the file"""
    logger.info("task started")
    start = time.time()
    try:
        process_csv_to_fhir(incoming_message_body=json.loads(event))
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing message: %s", error)
    end = time.time()
    print(f"Total time for completion:{round(end - start, 5)}s")


if __name__ == "__main__":
    main(event=os.environ.get("EVENT_DETAILS"))
