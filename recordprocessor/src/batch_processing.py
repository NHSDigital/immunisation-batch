import json
from io import StringIO
import os
import logging
from constants import Constants
from utils_for_recordprocessor import get_environment, fetch_file_from_s3
from get_action_flag_permissions import get_action_flag_permissions
from process_row import process_row
from update_ack_file import update_ack_file
from send_to_kinesis import send_to_kinesis


logging.basicConfig(level="INFO")
logger = logging.getLogger()


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
    action_flag_permissions = get_action_flag_permissions(supplier, vaccine_type)

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
        print(details_from_processing, "<<<<<<<DETAILS")
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
        accumulated_ack_file_content = update_ack_file(
            file_key,
            bucket_name,
            accumulated_ack_file_content,
            message_id,
            message_delivered,
            diagnostics,
        )

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
