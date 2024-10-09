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

s3_client = boto3.client("s3", config=Config(region_name="eu-west-2"))
logger = logging.getLogger()
cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


def get_environment():
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user workspaces
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def identify_supplier(file_key: str):
    """Identify the supplier using the ODS code in the file name"""
    supplier_match = re.search(r"_Vaccinations_v\d+_(\w+)_\d+T\d+\.csv$", file_key)
    ods_code = supplier_match.group(1).upper() if supplier_match else None
    return ODS_PATTERNS.get(ods_code, None)


def forward_request_to_api(
    message_header, bucket_name, file_key, action_flag, fhir_json, ack_bucket_name, imms_id, version
):
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")
    headers = Constants.ack_headers
    parts = file_key.split(".")
    ack_filename = f"forwardedFile/{parts[0]}_response.csv"

    accumulated_csv_content = StringIO()

    try:
        # Check if the acknowledgment file exists in S3
        s3_client.head_object(Bucket=ack_bucket_name, Key=ack_filename)
        # If it exists, download the file and accumulate its content
        existing_ack_file = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        existing_content = existing_ack_file["Body"].read().decode("utf-8")
        accumulated_csv_content.write(existing_content)
        print(f"accumulated_csv_content_existing:{accumulated_csv_content}")  # Add existing content to the StringIO
    except ClientError as e:
        logger.error(f"error:{e}")
        if e.response["Error"]["Code"] == "404":
            # File doesn't exist, write the header to the new file
            accumulated_csv_content.write("|".join(headers) + "\n")
            print(f"accumulated_csv_content:{accumulated_csv_content}")
    if fhir_json == "No_Permissions":
        data_row = Constants.data_rows("no permissions", created_at_formatted_string, message_header)
    else:
        if imms_id == "None" and version == "None":
            data_row = Constants.data_rows("None", created_at_formatted_string, message_header)
        supplier_system = identify_supplier(file_key)
        if action_flag == "new":
            response, status_code = immunization_api_instance.create_immunization(fhir_json, supplier_system)
            print(f"response:{response},status_code:{status_code}")
            if status_code == 201:
                data_row = Constants.data_rows(True, created_at_formatted_string, message_header)
            elif status_code == 422:
                data_row = Constants.data_rows("duplicate", created_at_formatted_string, message_header)
            else:
                data_row = Constants.data_rows(False, created_at_formatted_string, message_header)
        elif action_flag == "update" and imms_id not in (None, "None") and version not in (None, "None"):
            fhir_json["id"] = imms_id
            print(f"updated_fhir_json:{fhir_json}")
            response, status_code = immunization_api_instance.update_immunization(
                imms_id, version, fhir_json, supplier_system
            )
            print(f"response:{response},status_code:{status_code}")
            if status_code == 200:
                data_row = Constants.data_rows(True, created_at_formatted_string, message_header)
            else:
                data_row = Constants.data_rows(False, created_at_formatted_string, message_header)
        elif action_flag == "delete" and imms_id not in (None, "None"):
            response, status_code = immunization_api_instance.delete_immunization(imms_id, fhir_json, supplier_system)
            print(f"response:{response},status_code:{status_code}")
            if status_code == 204:
                data_row = Constants.data_rows(True, created_at_formatted_string, message_header)
            else:
                data_row = Constants.data_rows(False, created_at_formatted_string, message_header)

    data_row_str = [str(item) for item in data_row]
    cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()

    accumulated_csv_content.write(cleaned_row + "\n")
    print(f"CSV content before upload:\n{accumulated_csv_content.getvalue()}")
    # Upload the updated CSV content to S3
    csv_file_like_object = io.BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
    logger.info(f"Ack file updated to {ack_bucket_name}: {ack_filename}")


def forward_lambda_handler(event, context):
    imms_env = get_environment()
    bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-sources")
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-destinations")

    for record in event["Records"]:
        try:
            print(f"Records:{record}")
            # Extract the Kinesis data
            kinesis_payload = record["kinesis"]["data"]
            decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
            message_body = json.loads(decoded_payload)
            message_header = message_body.get("message_id")
            fhir_json = message_body.get("fhir_json")
            action_flag = message_body.get("action_flag")
            file_key = message_body.get("file_name")
            imms_id = None
            version = None
            if action_flag in ("update", "delete", "None"):
                imms_id = message_body.get("imms_id")
                version = message_body.get("version")
            forward_request_to_api(
                message_header, bucket_name, file_key, action_flag, fhir_json, ack_bucket_name, imms_id, version
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}")


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
