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
from constants import Constants
from models.authentication import AppRestrictedAuth, Service
from models.cache import Cache
from permissions_checker import get_permissions_config_json_from_s3
from utils_for_recordprocessor import get_environment
from s3_clients import s3_client, kinesis_client


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")
cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)


def get_supplier_permissions(supplier: str) -> list:
    """
    Returns the permissions for the given supplier. Returns an empty list if the permissions config json could not
    be downloaded, or the supplier has no permissions.
    """
    config_bucket_name = os.getenv("CONFIG_BUCKET_NAME", f"immunisation-batch-{get_environment()}-config")
    return get_permissions_config_json_from_s3(config_bucket_name).get("all_permissions", {}).get(supplier, [])


def get_action_flag_permissions(supplier, vaccine_type):
    vaccine_type = vaccine_type.upper()
    allowed_permissions = get_supplier_permissions(supplier)

    if f"{vaccine_type}_FULL" in allowed_permissions:
        return {"NEW", "UPDATE", "DELETE"}

    permission_operations = {perm.split("_")[1] for perm in allowed_permissions if perm.startswith(vaccine_type)}
    if "CREATE" in permission_operations:
        permission_operations.add("NEW")
        permission_operations.remove("CREATE")
    return permission_operations


def send_to_kinesis(supplier, message_body):
    """Send a message to the specified Kinesis stream."""
    logger.info(f"message_body:{message_body}")
    stream_name = SUPPLIER_SQSQUEUE_MAPPINGS.get(supplier, supplier)
    kinesis_queue_prefix = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")

    try:
        # Send the message to the Kinesis stream
        resp = kinesis_client.put_record(
            StreamName=f"{kinesis_queue_prefix}-processingdata-stream",
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


def add_row_to_ack_file(data_row, accumulated_ack_file_content, ack_bucket_name, ack_filename):
    data_row_str = [str(item) for item in data_row]
    cleaned_row = "|".join(data_row_str).replace(" |", "|").replace("| ", "|").strip()
    accumulated_ack_file_content.write(cleaned_row + "\n")
    csv_file_like_object = io.BytesIO(accumulated_ack_file_content.getvalue().encode("utf-8"))
    s3_client.upload_fileobj(csv_file_like_object, ack_bucket_name, ack_filename)
    logger.info(f"CSV content before upload with perms:\n{accumulated_ack_file_content.getvalue()}")
    return accumulated_ack_file_content


def handle_row(
    message_header,
    file_key,
    supplier,
    vaccine_type,
    ack_bucket_name,
    permission_operations,
    ack_filename,
    accumulated_ack_file_content,
    row,
    created_at_formatted_string,
):
    logger.info(f"messageheader : {message_header}")
    action_flag = row.get("ACTION_FLAG") or ""
    action_flag = action_flag.upper()
    logger.info(f"ACTION FLAG PERMISSIONS:  {action_flag}")
    logger.info(f"PERMISSIONS OPERATIONS {permission_operations}")

    message_body = {
        "message_id": message_header,
        "fhir_json": "No_Permissions",
        "action_flag": "No_Permissions",
        "imms_id": "None",
        "version": "None",
        "file_name": file_key,
    }

    # Handle no permissions
    if not (action_flag in permission_operations):
        logger.info(f"Skipping row as supplier does not have the permissions for this csv operation {action_flag}")

        data_row = Constants.data_rows("no permissions", created_at_formatted_string, message_header)
        status = send_to_kinesis(supplier, message_body)
        accumulated_ack_file_content = add_row_to_ack_file(
            data_row, accumulated_ack_file_content, ack_bucket_name, ack_filename
        )
        return accumulated_ack_file_content

    fhir_json, valid = convert_to_fhir_json(row, vaccine_type)

    # Hanlde missing UNIQUE_ID or UNIQUE_ID_URI or invalid conversion
    if not ((identifier_system := row.get("UNIQUE_ID_URI")) and (identifier_value := row.get("UNIQUE_ID")) and valid):
        logger.error(f"Invalid row format: row is missing either UNIQUE_ID or UNIQUE_ID_URI")
        message_body["fhir_json"] = "None"
        message_body["action_flag"] = "None"
        status = send_to_kinesis(supplier, message_body)
        if status:
            logger.info("sent successful invalid_json")
            data_row = Constants.data_rows("None", created_at_formatted_string, message_header)
        else:
            logger.error("Error sending to SQS for invliad json")
            data_row = Constants.data_rows(False, created_at_formatted_string, message_header)
        accumulated_ack_file_content = add_row_to_ack_file(
            data_row, accumulated_ack_file_content, ack_bucket_name, ack_filename
        )
        return accumulated_ack_file_content

    all_values_obtained = True if action_flag == "NEW" else False
    if action_flag in ("DELETE", "UPDATE"):
        response, status_code = immunization_api_instance.get_imms_id(identifier_system, identifier_value)
        if response.get("total") == 1 and status_code == 200:
            all_values_obtained = True

    # Handle unable to find in IEDS
    if not all_values_obtained:
        logger.info(f"imms_id not found:{response} and status_code:{status_code}")
        message_body["fhir_json"] = fhir_json
        message_body["action_flag"] = "None"
        status = send_to_kinesis(supplier, message_body)
        if status:
            logger.info("create successful imms not found")
            data_row = Constants.data_rows("None", created_at_formatted_string, message_header)
        else:
            logger.error("Error sending to SQS imms id not found")
            data_row = Constants.data_rows(False, created_at_formatted_string, message_header)
        accumulated_ack_file_content = add_row_to_ack_file(
            data_row, accumulated_ack_file_content, ack_bucket_name, ack_filename
        )
        return accumulated_ack_file_content

    # Prepare the message for Kinesis
    message_body["fhir_json"] = fhir_json
    message_body["action_flag"] = action_flag
    if action_flag in ("DELETE", "UPDATE"):
        entry = response.get("entry", [])[0]
        message_body["imms_id"] = entry["resource"].get("id")
        message_body["version"] = entry["resource"].get("meta", {}).get("versionId")

    status = send_to_kinesis(supplier, message_body)
    if status:
        logger.info("message sent successfully to Kinesis")
        data_row = Constants.data_rows(True, created_at_formatted_string, message_header)
    else:
        logger.error("Error sending to Kinesis")
        data_row = Constants.data_rows(False, created_at_formatted_string, message_header)

    accumulated_ack_file_content = add_row_to_ack_file(
        data_row, accumulated_ack_file_content, ack_bucket_name, ack_filename
    )
    return accumulated_ack_file_content


def process_csv_to_fhir(
    bucket_name,
    file_key,
    supplier,
    vaccine_type,
    ack_bucket_name,
    message_id,
    permission_operations,
):
    csv_data = fetch_file_from_s3(bucket_name, file_key)
    csv_reader = csv.DictReader(StringIO(csv_data), delimiter="|")
    response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
    created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

    headers = Constants.ack_headers
    ack_filename = f"processedFile/{file_key.replace('.csv', '_response.csv')}"

    accumulated_ack_file_content = StringIO()  # Initialize a variable to accumulate CSV content
    accumulated_ack_file_content.write("|".join(headers) + "\n")  # Write the header once at the start

    row_count = 0  # Initialize a counter for rows

    for row in csv_reader:
        row_count += 1
        message_header = f"{message_id}#{row_count}"
        accumulated_ack_file_content = handle_row(
            message_header,
            file_key,
            supplier,
            vaccine_type,
            ack_bucket_name,
            permission_operations,
            ack_filename,
            accumulated_ack_file_content,
            row,
            created_at_formatted_string,
        )

    logger.info(f"Total rows processed: {row_count}")  # logger the total number of rows processed


def main(event):
    imms_env = get_environment()
    bucket_name = os.getenv("SOURCE_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-source")
    ack_bucket_name = os.getenv("ACK_BUCKET_NAME", f"immunisation-batch-{imms_env}-data-destination")
    try:
        logger.info("task started")
        message_body_json = json.loads(event)
        logger.info(f"Event: {message_body_json}")
        message_id = message_body_json.get("message_id")
        vaccine_type = message_body_json.get("vaccine_type")
        supplier = message_body_json.get("supplier")
        file_key = message_body_json.get("filename")

        # Get permissions and determine processing logic
        permission_operations = get_action_flag_permissions(supplier, vaccine_type)
        process_csv_to_fhir(
            bucket_name=bucket_name,
            file_key=file_key,
            supplier=supplier,
            vaccine_type=vaccine_type,
            ack_bucket_name=ack_bucket_name,
            message_id=message_id,
            permission_operations=permission_operations,
        )

    except Exception as e:
        logger.error(f"Error processing message: {e}")


if __name__ == "__main__":
    event = os.environ.get("EVENT_DETAILS")
    creds = os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
    logger.info(f"creds: {creds}")
    main(event)
