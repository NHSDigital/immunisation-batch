import boto3
import json
from io import StringIO
import io
import os
import re
from immunisation_api import ImmunizationApi
import logging
from botocore.exceptions import ClientError
from botocore.config import Config
from constants import Constant
from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
from ods_patterns import ODS_PATTERNS

s3_client = boto3.client("s3", config=Config(region_name="eu-west-2"))
sqs_client = boto3.client("sqs", config=Config(region_name="eu-west-2"))
logger = logging.getLogger()
cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


def get_environment():
    _env = os.getenv("ENVIRONMENT")
    non_prod = ["internal-dev", "int", "ref", "sandbox"]
    if _env in non_prod:
        return _env
    elif _env == "prod":
        return "prod"
    else:
        return "internal-dev"  # default to internal-dev for pr and user workspaces


def identify_supplier(file_key: str):
    """Identify the supplier using the ODS code in the file name"""
    supplier_match = re.search(r"_Vaccinations_v\d+_(\w+)_\d+T\d+\.csv$", file_key)
    ods_code = supplier_match.group(1).upper() if supplier_match else None
    return ODS_PATTERNS.get(ods_code, None)


def forward_request_to_api(bucket_name, file_key, action_flag, fhir_json, ack_bucket_name, imms_id, version):
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at = response["LastModified"]
    created_at_formatted = created_at.strftime("%Y%m%dT%H%M%S00")
    headers = Constant.header
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
    if imms_id == "None" and version == "None":
        print("1")
        data_row = Constant.data_rows(False, created_at_formatted)
    supplier_system = identify_supplier(file_key)
    print("3")
    if action_flag == "new":
        response, status_code = immunization_api_instance.create_immunization(fhir_json, supplier_system)
        print(f"response:{response},status_code:{status_code}")
        if status_code == 201:
            data_row = Constant.data_rows(True, created_at_formatted)
        elif status_code == 422:
            data_row = Constant.data_rows("duplicate", created_at_formatted)
        else:
            data_row = Constant.data_rows(False, created_at_formatted)
    elif action_flag == "update" and imms_id not in (None, "None") and version not in (None, "None"):
        fhir_json["id"] = imms_id
        print(f"updated_fhir_json:{fhir_json}")
        response, status_code = immunization_api_instance.update_immunization(
            imms_id, version, fhir_json, supplier_system
        )
        print(f"response:{response},status_code:{status_code}")
        if status_code == 200:
            data_row = Constant.data_rows(True, created_at_formatted)
        else:
            data_row = Constant.data_rows(False, created_at_formatted)
    elif action_flag == "delete" and imms_id not in (None, "None"):
        response, status_code = immunization_api_instance.delete_immunization(imms_id, fhir_json, supplier_system)
        print(f"response:{response},status_code:{status_code}")
        if status_code == 204:
            data_row = Constant.data_rows(True, created_at_formatted)
        else:
            data_row = Constant.data_rows(False, created_at_formatted)

    data_row_str = [str(item) for item in data_row]
    cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()

    accumulated_csv_content.write(cleaned_row + "\n")

    # Upload the updated CSV content to S3
    csv_file_like_object = io.BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
    logger.info(f"Ack file updated to {ack_bucket_name}: {ack_filename}")


def forward_lambda_handler(event, context):
    imms_env = get_environment()
    bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-source")
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-destination")

    for record in event["Records"]:
        try:
            print(f"Records:{record}")
            message_body = json.loads(record["body"])
            fhir_json = message_body.get("fhir_json")
            action_flag = message_body.get("action_flag")
            file_key = message_body.get("file_name")
            imms_id = None
            version = None
            if action_flag in ("update", "delete"):
                imms_id = message_body.get("imms_id")
                version = message_body.get("version")
            forward_request_to_api(bucket_name, file_key, action_flag, fhir_json, ack_bucket_name, imms_id, version)

        except Exception as e:
            logger.error(f"Error processing message: {e}")


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
