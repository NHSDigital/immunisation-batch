"""Functions for adding a row of data to the ack file"""

import logging
import io
import os
from typing import Union
from s3_clients import s3_client
from utils_for_recordprocessor import get_environment

logger = logging.getLogger()


def create_ack_data(
    created_at_formatted_string: str, row_id: str, delivered: bool, diagnostics: Union[None, str] = None
):
    """Returns a dictionary containing the ack headers as keys, along with the relevant values."""
    return {
        "MESSAGE_HEADER_ID": row_id,
        "HEADER_RESPONSE_CODE": "fatal-error" if diagnostics else "ok",
        "ISSUE_SEVERITY": "error" if diagnostics else "information",
        "ISSUE_CODE": "error" if diagnostics else "informational",
        "RESPONSE_TYPE": "business",
        "RESPONSE_CODE": "20005" if diagnostics else "20013",
        "RESPONSE_DISPLAY": diagnostics if diagnostics else "Success",
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "TBC",
        "LOCAL_ID": "DPS",
        "MESSAGE_DELIVERY": delivered,
    }


def add_row_to_ack_file(ack_data, accumulated_ack_file_content, file_key):
    """Adds the data row to the uploaded ack file"""
    data_row_str = [str(item) for item in ack_data.values()]
    cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
    accumulated_ack_file_content.write(cleaned_row + "\n")
    csv_file_like_object = io.BytesIO(accumulated_ack_file_content.getvalue().encode("utf-8"))
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{get_environment()}-data-destinations")
    ack_filename = f"processedFile/{file_key.replace('.csv', '_response.csv')}"
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
    logger.info("CSV content before upload with perms:\n%s", accumulated_ack_file_content.getvalue())
    return accumulated_ack_file_content


def update_ack_file(
    file_key: str,
    bucket_name: str,
    accumulated_ack_file_content,
    row_id: str,
    message_delivered: bool,
    diagnostics: Union[None, str] = None,
):
    """Updates the ack file with the new data row based on the given arguments"""
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")
    ack_data_row = create_ack_data(created_at_formatted_string, row_id, message_delivered, diagnostics)
    accumulated_ack_file_content = add_row_to_ack_file(ack_data_row, accumulated_ack_file_content, file_key)
    return accumulated_ack_file_content
