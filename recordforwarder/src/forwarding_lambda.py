import boto3
import json
from io import StringIO
import io
import os
import re
import base64
from immunisation_api import ImmunizationApi
import logging
from botocore.exceptions import ClientError
from botocore.config import Config
from constants import Constants
from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
from ods_patterns import ODS_PATTERNS
from update_ack_file import create_ack_data
from utils_for_record_forwarder import get_environment

s3_client = boto3.client("s3", config=Config(region_name="eu-west-2"))
logger = logging.getLogger()
cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


def identify_supplier(file_key: str):
    """Identify the supplier using the ODS code in the file name"""
    supplier_match = re.search(r"_Vaccinations_v\d+_(\w+)_\d+T\d+\.csv$", file_key)
    ods_code = supplier_match.group(1).upper() if supplier_match else None
    return ODS_PATTERNS.get(ods_code, None)


def forward_request_to_api(message_body):
    row_id = message_body.get("message_id")
    fhir_json = message_body.get("fhir_json")
    action_flag = message_body.get("action_flag")
    file_key = message_body.get("file_name")
    imms_id = message_body.get("imms_id")
    version = message_body.get("version")

    imms_env = get_environment()
    source_bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-sources")
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-destinations")

    response = s3_client.head_object(Bucket=source_bucket_name, Key=file_key)
    created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

    message_delivered = False
    diagnostics = None
    response_code = None

    if fhir_json == "No_Permissions":
        diagnostics = "Skipped As No permissions for operation"
        response_code = "20005"

    else:

        if imms_id == "None" and version == "None":
            diagnostics = "failed in json conversion"
            response_code = "20005"

        supplier_system = identify_supplier(file_key)

        if action_flag == "new":
            response, status_code = immunization_api_instance.create_immunization(fhir_json, supplier_system)
            print(f"response:{response},status_code:{status_code}")
            if status_code == 201:
                response_code = "20013"
                message_delivered = True
            elif status_code == 422:
                diagnostics = "Duplicate Message received"
                response_code = "20007"
            else:
                diagnostics = "Payload validation failure"
                response_code = "20009"

        elif action_flag == "update" and imms_id not in (None, "None") and version not in (None, "None"):
            fhir_json["id"] = imms_id
            response, status_code = immunization_api_instance.update_immunization(
                imms_id, version, fhir_json, supplier_system
            )
            print(f"response:{response},status_code:{status_code}")
            if status_code == 200:
                response_code = "20013"
            else:
                diagnostics = "Payload validation failure"
                response_code = "20009"

        elif action_flag == "delete" and imms_id not in (None, "None"):
            response, status_code = immunization_api_instance.delete_immunization(imms_id, fhir_json, supplier_system)
            print(f"response:{response},status_code:{status_code}")
            if status_code == 204:
                response_code = "20013"
                message_delivered = True
            else:
                diagnostics = "Payload validation failure"
                response_code = "20009"

    ack_data = create_ack_data(created_at_formatted_string, row_id, message_delivered, response_code, diagnostics)

    accumulated_csv_content = StringIO()
    headers = Constants.ack_headers
    parts = file_key.split(".")
    ack_filename = f"forwardedFile/{parts[0]}_response.csv"
    try:
        # Check if the acknowledgment file exists in S3
        s3_client.head_object(Bucket=ack_bucket_name, Key=ack_filename)
        # If it exists, download the file and accumulate its content
        existing_ack_file = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        existing_content = existing_ack_file["Body"].read().decode("utf-8")
        accumulated_csv_content.write(existing_content)
    except ClientError as error:
        logger.error("error:%s", error)
        if error.response["Error"]["Code"] == "404":
            # File doesn't exist, write the header to the new file
            accumulated_csv_content.write("|".join(headers) + "\n")
        else:
            raise
    data_row_str = [str(item) for item in ack_data.values()]
    cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()

    accumulated_csv_content.write(cleaned_row + "\n")
    print(f"CSV content before upload:\n{accumulated_csv_content.getvalue()}")
    # Upload the updated CSV content to S3
    csv_file_like_object = io.BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
    logger.info(f"Ack file updated to {ack_bucket_name}: {ack_filename}")


def forward_lambda_handler(event, _):
    """Forward each row to the Imms API"""

    for record in event["Records"]:
        try:
            # Extract the Kinesis data
            kinesis_payload = record["kinesis"]["data"]
            decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
            message_body = json.loads(decoded_payload)
            forward_request_to_api(message_body)
        except Exception as error:  # pylint:disable=broad-exception-caught
            logger.error("Error processing message: %s", error)


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
