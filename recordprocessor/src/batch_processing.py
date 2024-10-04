import boto3
import csv
import json
from io import StringIO
import io
import os
from convert_fhir_json import convert_to_fhir_json
from get_imms_id import ImmunizationApi
import logging
from ods_patterns import SUPPLIER_SQSQUEUE_MAPPINGS
from botocore.exceptions import ClientError
from botocore.config import Config
from constants import Constant
from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
from permissions_checker import get_json_from_s3


# Initialize Kinesis client instead of SQS.
kinesis_client = boto3.client("kinesis", config=Config(region_name="eu-west-2"))
s3_client = boto3.client("s3", config=Config(region_name="eu-west-2"))
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
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


def get_supplier_permissions(supplier, config_bucket_name):
    supplier_permissions = get_json_from_s3(config_bucket_name)
    logger.info(f"config_perms_check: {supplier_permissions}")
    if supplier_permissions is None:
        return []
    all_permissions = supplier_permissions.get("all_permissions", {})
    logger.info(f"Extracted All Supplier permissions:{all_permissions}")
    return all_permissions.get(supplier, [])


def validate_full_permissions(config_bucket_name, supplier, vaccine_type):
    allowed_permissions = get_supplier_permissions(supplier, config_bucket_name)
    allowed_permissions_set = set(allowed_permissions)
    logger.info(f"Supplier Allowed Permissions: {allowed_permissions_set}")
    return f"{vaccine_type.upper()}_FULL" in allowed_permissions_set


def get_permission_operations(supplier, config_bucket_name, vaccine_type):
    allowed_permissions = get_supplier_permissions(supplier, config_bucket_name)
    permission_operations = {
        perm.split("_")[1] for perm in allowed_permissions if perm.startswith(vaccine_type.upper())
    }
    if "CREATE" in permission_operations:
        permission_operations.add("NEW")
        permission_operations.remove("CREATE")
    logger.info(f"Supplier Allowed Operation Permissions: {permission_operations}")

    return permission_operations


def send_to_kinesis(supplier, message_body):
    """Send a message to the specified Kinesis stream."""
    logger.info(f"message_body:{message_body}")
    stream_name = SUPPLIER_SQSQUEUE_MAPPINGS.get(supplier, supplier)
    imms_shrt_prefix = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")

    try:
        # Send the message to the Kinesis stream
        resp = kinesis_client.put_record(
            StreamName=f"{imms_shrt_prefix}-processingdata-stream",
            StreamARN=os.getenv("KINESIS_STREAM_ARN"),
            Data=json.dumps(message_body, ensure_ascii=False),
            PartitionKey=supplier,  # Use a partition key
        )
        logger.info(f"Message sent to Kinesis stream:{stream_name} for supplier:{supplier} with resp:{resp}")
    except ClientError as e:
        logger.error(f"Error sending message to Kinesis: {e}")
        return False
    return True


def fetch_file_from_s3(bucket_name, file_key):
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    return response["Body"].read().decode("utf-8")


def process_csv_to_fhir(
    bucket_name,
    file_key,
    supplier,
    vaccine_type,
    ack_bucket_name,
    message_id,
    full_permissions,
    permission_operations,
):
    csv_data = fetch_file_from_s3(bucket_name, file_key)
    csv_reader = csv.DictReader(StringIO(csv_data), delimiter="|")
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at = response["LastModified"]
    created_at_formatted = created_at.strftime("%Y%m%dT%H%M%S00")

    headers = Constant.header
    parts = file_key.split(".")
    ack_filename = f"processedFile/{parts[0]}_response.csv"

    accumulated_csv_content = StringIO()  # Initialize a variable to accumulate CSV content
    accumulated_csv_content.write("|".join(headers) + "\n")  # Write the header once at the start

    row_count = 0  # Initialize a counter for rows

    for row in csv_reader:
        logger.info(f"row:{row}")
        row_count += 1
        message_header = f"{message_id}#{row_count}"
        logger.info(f"messageheader : {message_header}")
        logger.info(f"parsed_row:{row}")
        action_flag_perms = row.get("ACTION_FLAG", "")
        logger.info(f"ACTION FLAG PERMISSIONS:  {action_flag_perms}")
        if action_flag_perms is None:
            action_flag_perms = ""
            logger.info(f"FULL PERMISSIONS: {full_permissions} AND PERMISSIONS OPERATIONS {permission_operations}")
        if not (full_permissions or action_flag_perms.upper() in permission_operations):
            logger.info(
                f"Skipping row as supplier does not have the permissions for this csv operation {action_flag_perms}"
            )

            message_body = {
                "message_id": message_header,
                "fhir_json": "No_Permissions",
                "action_flag": "No_Permissions",
                "imms_id": "None",
                "version": "None",
                "file_name": file_key,
            }

            data_row = Constant.data_rows("no permissions", created_at_formatted, message_header)
            data_row_str = [str(item) for item in data_row]
            cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
            accumulated_csv_content.write(cleaned_row + "\n")
            csv_file_like_object = io.BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))
            s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
            logger.info(f"CSV content before upload with perms:\n{accumulated_csv_content.getvalue()}")
            status = send_to_kinesis(supplier, message_body)
            continue
        if row.get("ACTION_FLAG") in {"new", "update", "delete"} and row.get("UNIQUE_ID_URI") and row.get("UNIQUE_ID"):
            fhir_json, valid = convert_to_fhir_json(row, vaccine_type)
            if valid:
                identifier_system = row.get("UNIQUE_ID_URI")
                action_flag = row.get("ACTION_FLAG")
                identifier_value = row.get("UNIQUE_ID")
                logger.info(f"Successfully converted row to FHIR: {fhir_json}")
                flag = True
                if action_flag in ("delete", "update"):
                    flag = False
                    response, status_code = immunization_api_instance.get_imms_id(identifier_system, identifier_value)
                    if response.get("total") == 1 and status_code == 200:
                        flag = True
                if flag:
                    # Prepare the message for Kinesis
                    if action_flag == "new":
                        message_body = {
                            "message_id": message_header,
                            "fhir_json": fhir_json,
                            "action_flag": action_flag,
                            "file_name": file_key,
                        }
                    if action_flag in ("delete", "update"):
                        entry = response.get("entry", [])[0]
                        imms_id = entry["resource"].get("id")
                        version = entry["resource"].get("meta", {}).get("versionId")
                        message_body = {
                            "message_id": message_header,
                            "fhir_json": fhir_json,
                            "action_flag": action_flag,
                            "imms_id": imms_id,
                            "version": version,
                            "file_name": file_key,
                        }
                    status = send_to_kinesis(supplier, message_body)
                    if status:
                        logger.info("create successful")
                        logger.info("message sent successfully to Kinesis")
                        data_row = Constant.data_rows(True, created_at_formatted, message_header)
                    else:
                        logger.error("Error sending to Kinesis")
                        data_row = Constant.data_rows(False, created_at_formatted, message_header)

                else:
                    logger.info(f"imms_id not found:{response} and status_code:{status_code}")
                    message_body = {
                        "message_id": message_header,
                        "fhir_json": fhir_json,
                        "action_flag": "None",
                        "imms_id": "None",
                        "version": "None",
                        "file_name": file_key,
                    }
                    status = send_to_kinesis(supplier, message_body)
                    if status:
                        logger.info("create successful imms not found")
                        logger.info("message sent successfully to SQS")
                        data_row = Constant.data_rows("None", created_at_formatted, message_header)
                    else:
                        logger.error("Error sending to SQS imms id not found")
                        data_row = Constant.data_rows(False, created_at_formatted, message_header)
            else:
                logger.error(f"Invalid FHIR conversion for row: {row}")
                message_body = {
                    "message_id": message_header,
                    "fhir_json": fhir_json,
                    "action_flag": "None",
                    "imms_id": "None",
                    "version": "None",
                    "file_name": file_key,
                }
                status = send_to_kinesis(supplier, message_body)
                if status:
                    logger.info("sent successful invalid_json")
                    logger.info("message sent successfully to SQS")
                    data_row = Constant.data_rows("None", created_at_formatted, message_header)
                else:
                    logger.error("Error sending to SQS for invliad json")
                    data_row = Constant.data_rows(False, created_at_formatted, message_header)
        else:
            logger.error(f"Invalid row format: {row}")
            message_body = {
                "message_id": message_header,
                "fhir_json": "None",
                "action_flag": "None",
                "imms_id": "None",
                "version": "None",
                "file_name": file_key,
            }
            status = send_to_kinesis(supplier, message_body)
            if status:
                logger.info("sent successful invalid_json")
                logger.info("message sent successfully to SQS")
                data_row = Constant.data_rows("None", created_at_formatted, message_header)
            else:
                logger.error("Error sending to SQS for invliad json")
                data_row = Constant.data_rows(False, created_at_formatted, message_header)

        # Convert all elements in data_row to strings
        data_row_str = [str(item) for item in data_row]
        cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()

        # Write the cleaned and aligned data row to the accumulated CSV content
        accumulated_csv_content.write(cleaned_row + "\n")

        # Write the data row to the accumulated CSV content
        # accumulated_csv_content.write('|'.join(data_row_str) + '\n')

        # Upload to S3 after processing this row
        # csv_bytes = BytesIO(accumulated_csv_content.getvalue().encode('utf-8'))
        logger.info(f"CSV content before upload:\n{accumulated_csv_content.getvalue()}")
        csv_file_like_object = io.BytesIO(accumulated_csv_content.getvalue().encode("utf-8"))
        s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
        logger.info(f"Ack file updated to {ack_bucket_name}: {ack_filename}")

    logger.info(f"Total rows processed: {row_count}")  # logger the total number of rows processed


def main(event):
    imms_env = get_environment()
    bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-sources")
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-destinations")
    config_bucket_name = os.getenv(
        "CONFIG_BUCKET_NAME",
        f"immunisation-batch-{imms_env}-configs",
    )
    try:
        logger.info("task started")
        message_body_json = json.loads(event)
        logger.info(f"Event: {message_body_json}")
        permission = message_body_json.get("permission")
        message_id = message_body_json.get("message_id")
        vaccine_type = message_body_json.get("vaccine_type")
        supplier = message_body_json.get("supplier")
        file_key = message_body_json.get("filename")
        print(f"permission:{permission}")
        # Get permissions and determine processing logic
        full_permissions = validate_full_permissions(config_bucket_name, supplier, vaccine_type)
        permission_operations = get_permission_operations(supplier, config_bucket_name, vaccine_type)
        process_csv_to_fhir(
            bucket_name=bucket_name,
            file_key=file_key,
            supplier=supplier,
            vaccine_type=vaccine_type,
            ack_bucket_name=ack_bucket_name,
            message_id=message_id,
            full_permissions=full_permissions,
            permission_operations=permission_operations,
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}")


if __name__ == "__main__":
    event = os.environ.get("EVENT_DETAILS")
    creds = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
    logger.info(f"creds: {creds}")
    main(event)
