"""Functions for processing the file on a row-by-row basis"""

import json
from io import StringIO
import os
import logging
from constants import Constants
from utils_for_recordprocessor import get_environment, get_csv_content_dict_reader
from get_operation_permissions import get_operation_permissions
from process_row import process_row
from update_ack_file import update_ack_file
from send_to_kinesis import send_to_kinesis


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
    vaccine_type = incoming_message_body.get("vaccine_type").upper()
    supplier = incoming_message_body.get("supplier").upper()
    file_key = incoming_message_body.get("filename")
    action_flag_permissions = get_operation_permissions(supplier, vaccine_type)

    # Fetch the data
    bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-sources")
    csv_reader = get_csv_content_dict_reader(bucket_name, file_key)

    # Initialise the accumulated_ack_file_content with the headers
    accumulated_ack_file_content = StringIO()
    accumulated_ack_file_content.write("|".join(Constants.ack_headers) + "\n")

    row_count = 0  # Initialize a counter for rows
    for row in csv_reader:
        row_count += 1
        row_id = f"{file_id}#{row_count}"
        logger.info("MESSAGE ID : %s", row_id)

        # Process the row to obtain the details needed for the message_body and ack file
        cleaned_row = {key.strip(): value.strip().strip('"') for key, value in row.items()}
        details_from_processing = process_row(vaccine_type, action_flag_permissions, cleaned_row)

        # Create the message body for sending
        outgoing_message_body = {
            "row_id": row_id,
            "file_key": file_key,
            "supplier": supplier,
            **details_from_processing,
        }

        # Send to kinesis. Add diagnostics if send fails.
        message_delivered = send_to_kinesis(supplier, outgoing_message_body)
        if (diagnostics := details_from_processing.get("diagnostics")) is None and message_delivered is False:
            diagnostics = "Unsupported file type received as an attachment"

        # Update the ack file
        accumulated_ack_file_content = update_ack_file(
            file_key, bucket_name, accumulated_ack_file_content, row_id, message_delivered, diagnostics
        )

    logger.info("Total rows processed: %s", row_count)


def main(event: str) -> None:
    """Process each row of the file"""
    logger.info("task started")
    try:
        process_csv_to_fhir(incoming_message_body=json.loads(event))
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.error("Error processing message: %s", error)


if __name__ == "__main__":
    main(event=os.environ.get("EVENT_DETAILS"))
