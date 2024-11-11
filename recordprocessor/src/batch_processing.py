"""Functions for processing the file on a row-by-row basis"""

import json
from io import StringIO
import os
import logging
from constants import Constants
from utils_for_recordprocessor import get_environment, get_csv_content_dict_reader
from get_operation_permissions import get_operation_permissions
from process_row import process_row
from mappings import Vaccine
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
    vaccine: Vaccine = next(  # Convert vaccine_type to Vaccine enum
        vaccine for vaccine in Vaccine if vaccine.value == incoming_message_body.get("vaccine_type").upper()
    )
    supplier = incoming_message_body.get("supplier").upper()
    file_key = incoming_message_body.get("filename")
    permission = incoming_message_body.get("permission")
    allowed_operations = get_operation_permissions(vaccine, permission)

    # Fetch the data
    bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-sources")
    csv_reader = get_csv_content_dict_reader(bucket_name, file_key)

    # Initialize the accumulated_ack_file_content with the headers
    accumulated_ack_file_content = StringIO()
    accumulated_ack_file_content.write("|".join(Constants.ack_headers) + "\n")

    row_count = 0  # Initialize a counter for rows
    batch = []  
    batch_size = 10 

    for row in csv_reader:
        row_count += 1
        row_id = f"{file_id}#{row_count}"
        logger.info("MESSAGE ID : %s", row_id)

        # Process the row to obtain the details needed for the message body and ack file
        details_from_processing = process_row(vaccine, allowed_operations, row)

        # Create the message body for sending
        outgoing_row_data = {
            "row_id": row_id,
            "file_key": file_key,
            "supplier": supplier,
            **details_from_processing,
        }

        # Add the row data to the batch
        batch.append(outgoing_row_data)

        # When the batch reaches the batch size, send it as a single message to Kinesis
        if len(batch) == batch_size:
            outgoing_message_body = {
                "file_key": file_key,
                "supplier": supplier,
                "batch_rows": batch  # Add the batch of 30 rows to the message
            }

            # Send to Kinesis and handle diagnostics if send fails
            message_delivered = send_to_kinesis(supplier, outgoing_message_body)
            if not message_delivered:
                for row_data in batch:
                    row_data.setdefault("diagnostics", "Failed to send batch message to Kinesis")

            # Update the ack file for each row in the batch
            # for row_data in batch:
            #     accumulated_ack_file_content = update_ack_file(
            #         file_key,
            #         bucket_name,
            #         accumulated_ack_file_content,
            #         row_data["row_id"],
            #         message_delivered,
            #         row_data.get("diagnostics"),
            #         row_data.get("imms_id"),
            #     )

            # Clear the batch after sending
            batch.clear()

    # If there are any remaining rows after the loop, send them as a final message
    if batch:
        print("started")
        outgoing_message_body = {
            "file_key": file_key,
            "supplier": supplier,
            "batch_rows": batch  # Remaining rows as the final batch
        }

        message_delivered = send_to_kinesis(supplier, outgoing_message_body)
        if not message_delivered:
            for row_data in batch:
                row_data.setdefault("diagnostics", "Failed to send final batch message to Kinesis")

        # Update the ack file for each remaining row
        # for row_data in batch:
        #     accumulated_ack_file_content = update_ack_file(
        #         file_key,
        #         bucket_name,
        #         accumulated_ack_file_content,
        #         row_data["row_id"],
        #         message_delivered,
        #         row_data.get("diagnostics"),
        #         row_data.get("imms_id"),
        #     )

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
