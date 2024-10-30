"""Functions for adding a row of data to the ack file"""

import logging
import os
from io import StringIO, BytesIO
from typing import Union
from botocore.exceptions import ClientError
from clients import s3_client
from constants import Constants
from utils_for_record_forwarder import get_environment

logger = logging.getLogger()


def create_ack_data(
    created_at_formatted_string: str,
    row_id: str,
    successful_api_response: bool,
    diagnostics: Union[None, str] = None,
    imms_id: str = None,
) -> dict:
    """Returns a dictionary containing the ack headers as keys, along with the relevant values."""
    # Pack multi-line diagnostics down to single line (because Imms API diagnostics may be multi-line)
    diagnostics = (
        " ".join(diagnostics.replace("\r", " ").replace("\n", " ").replace("\t", " ").replace("\xa0", " ").split())
        if diagnostics is not None
        else None
    )
    return {
        "MESSAGE_HEADER_ID": row_id,
        "HEADER_RESPONSE_CODE": "OK" if successful_api_response else "Fatal Error",
        "ISSUE_SEVERITY": "Information" if not diagnostics else "Fatal",
        "ISSUE_CODE": "OK" if not diagnostics else "Fatal Error",
        "ISSUE_DETAILS_CODE": "30001" if not diagnostics else "30002",
        "RESPONSE_TYPE": "Business",
        "RESPONSE_CODE": "30001" if successful_api_response else "30002",
        "RESPONSE_DISPLAY": (
            "Success" if successful_api_response else "Business Level Response Value - Processing Error"
        ),
        "RECEIVED_TIME": created_at_formatted_string,
        "MAILBOX_FROM": "",  # TODO: Leave blank for DPS, use mailbox name if picked up from MESH mail box
        "LOCAL_ID": "",  # TODO: Leave blank for DPS, obtain from ctl file if picked up from MESH mail box
        "IMMS_ID": imms_id or "",
        "OPERATION_OUTCOME": diagnostics or "",
        "MESSAGE_DELIVERY": successful_api_response,
    }


def obtain_current_ack_content(ack_bucket_name: str, ack_file_key: str) -> StringIO:
    """Returns the current ack file content if the file exists, or else initialises the content with the ack headers."""
    accumulated_csv_content = StringIO()
    try:
        # If ack file exists in S3 download the contents
        existing_ack_file = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_file_key)
        existing_content = existing_ack_file["Body"].read().decode("utf-8")
        accumulated_csv_content.write(existing_content)
    except ClientError as error:
        logger.error("error:%s", error)
        if error.response["Error"]["Code"] in ("404", "NoSuchKey"):
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
    logger.info("Ack file updated to %s: %s", ack_bucket_name, ack_file_key)


def update_ack_file(
    file_key: str, row_id: str, successful_api_response: bool, diagnostics: Union[None, str], imms_id: Union[None, str]
) -> None:
    """Updates the ack file with the new data row based on the given arguments"""
    imms_env = get_environment()
    source_bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-sources")
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-destinations")
    ack_file_key = f"forwardedFile/{file_key.replace('.csv', '_BusAck.csv')}"
    response = s3_client.head_object(Bucket=source_bucket_name, Key=file_key)
    created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

    ack_data_row = create_ack_data(created_at_formatted_string, row_id, successful_api_response, diagnostics, imms_id)
    accumulated_csv_content = obtain_current_ack_content(ack_bucket_name, ack_file_key)
    upload_ack_file(ack_bucket_name, ack_file_key, accumulated_csv_content, ack_data_row)
