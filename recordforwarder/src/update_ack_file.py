"""Functions for adding a row of data to the ack file"""

import logging
import os
from io import StringIO, BytesIO
from typing import Union
from botocore.exceptions import ClientError
from s3_clients import s3_client
from constants import Constants
from utils_for_record_forwarder import get_environment

logger = logging.getLogger()


def create_ack_data(
    created_at_formatted_string: str,
    row_id: str,
    delivered: bool,
    response_code: str,
    diagnostics: Union[None, str] = None,
) -> dict:
    """Returns a dictionary containing the ack headers as keys, along with the relevant values."""
    return {
        "MESSAGE_HEADER_ID": row_id,
        "HEADER_RESPONSE_CODE": "fatal-error" if diagnostics else "ok",
        "ISSUE_SEVERITY": "error" if diagnostics else "information",
        "ISSUE_CODE": "error" if diagnostics else "informational",
        "RESPONSE_TYPE": "business",
        "RESPONSE_CODE": response_code,
        "RESPONSE_DISPLAY": diagnostics if diagnostics else "Success",
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "TBC",
        "LOCAL_ID": "DPS",
        "MESSAGE_DELIVERY": delivered,
    }


def obtain_current_ack_content(ack_bucket_name: str, ack_file_key: str) -> StringIO:
    """Returns the current ack file content if the file exists, or else initialises the content with the ack headers."""
    accumulated_csv_content = StringIO()
    try:
        # If ack file exists in S3 download the contents
        s3_client.head_object(Bucket=ack_bucket_name, Key=ack_file_key)
        existing_ack_file = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_file_key)
        existing_content = existing_ack_file["Body"].read().decode("utf-8")
        accumulated_csv_content.write(existing_content)
    except ClientError as error:
        logger.error("error:%s", error)
        if error.response["Error"]["Code"] == "404":
            # If ack file does not exist in S3 create a new file
            accumulated_csv_content.write("|".join(Constants.ack_headers) + "\n")
        else:
            raise
    return accumulated_csv_content


def upload_ack_file(
    ack_bucket_name: str, ack_file_key: str, accumulated_csv_content: StringIO, ack_data_row: dict
) -> None:
    """Adds the data row to the uploaded ack file"""
    data_row_str = [str(item) for item in ack_data_row.values()]
    cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
    accumulated_csv_content.write(cleaned_row + "\n")
    csv_file_like_object = BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_file_key)
    print(f"CSV content before upload:\n{accumulated_csv_content.getvalue()}")
    logger.info("Ack file updated to %s: %s", ack_bucket_name, ack_file_key)


def update_ack_file(file_key: str, row_id: str, message_delivered: bool, response_code: str, diagnostics: str) -> None:
    """Updates the ack file with the new data row based on the given arguments"""
    imms_env = get_environment()
    source_bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-sources")
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-destinations")
    ack_file_key = f"forwardedFile/{file_key.split('.')[0]}_response.csv"
    response = s3_client.head_object(Bucket=source_bucket_name, Key=file_key)
    created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

    ack_data_row = create_ack_data(created_at_formatted_string, row_id, message_delivered, response_code, diagnostics)
    accumulated_csv_content = obtain_current_ack_content(ack_bucket_name, ack_file_key)
    upload_ack_file(ack_bucket_name, ack_file_key, accumulated_csv_content, ack_data_row)
