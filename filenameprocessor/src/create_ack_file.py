import csv
import os
from io import StringIO, BytesIO
from utils_for_filenameprocessor import get_environment


def create_ack_file(
    message_id: str, file_key: str, validation_passed: bool, message_delivery: bool, created_at_formatted, s3_client
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
