"""Functions for initial file validation"""

import logging
import os
import signal
from re import match
from datetime import datetime
from constants import Constants
from fetch_permissions import get_permissions_config_json_from_cache
from utils_for_filenameprocessor import extract_file_key_elements
from s3_clients import dynamodb_client
from uuid import uuid4

logger = logging.getLogger()


# Define a timeout exception
class TimeoutError(Exception):
    pass


# Function to handle timeout
def timeout_handler(signum, frame):
    raise TimeoutError("Task timed out")


def add_to_audit_table(file_key: str) -> bool:
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)  # Set the timeout for the task
    message_id = str(uuid4())

    try:
        dynamodb_client.put_item(
            TableName=os.environ["AUDIT_TABLE_NAME"],
            Item={
                "message_id": {"S": message_id},
                "filename": {"S": file_key},
                "status": {"S": "testing"},
                "timestamp": {"S": "TBC"},
            },
        )
        logger.info("%s file, with message id %s, successfully added to audit table", file_key, message_id)
        signal.alarm(0)

    except TimeoutError as error:
        logger.error("Unable to add to audit table. Error: %s", error)
        signal.alarm(0)
        return False

    return True


def is_valid_datetime(timestamp: str) -> bool:
    """
    Returns a bool to indicate whether the timestamp is a valid datetime in the format 'YYYYmmddTHHMMSSzz'
    where 'zz' is a two digit number indicating the timezone
    """
    # Check that datetime (excluding timezone) is a valid datetime in the expected format.
    if len(timestamp) < 15:
        return False

    # Note that any digits after the seconds (i.e. from the 16th character onwards, usually expected to represent
    # timezone), do not need to be validated
    try:
        datetime.strptime(timestamp[:15], "%Y%m%dT%H%M%S")
    except ValueError:
        return False

    return True


def get_supplier_permissions(supplier: str) -> list:
    """
    Returns the permissions for the given supplier. Returns an empty list if the permissions config json could not
    be downloaded, or the supplier has no permissions.
    """
    return get_permissions_config_json_from_cache().get("all_permissions", {}).get(supplier, [])


def validate_vaccine_type_permissions(supplier: str, vaccine_type: str):
    """Returns True if the given supplier has any permissions for the given vaccine type, else False"""
    allowed_permissions = get_supplier_permissions(supplier)
    return vaccine_type in " ".join(allowed_permissions)


def initial_file_validation(file_key: str):
    """
    Returns True if all elements of file key are valid, content headers are valid and the supplier has the
    appropriate permissions. Else returns False.
    """
    # Add file to audit table and confirm it is not a duplicate
    add_to_audit_table(file_key)

    # Validate file name format (must contain four '_' a single '.' which occurs after the four '_'
    if not match(r"^[^_.]*_[^_.]*_[^_.]*_[^_.]*_[^_.]*\.[^_.]*$", file_key):
        logger.error("Initial file validation failed: invalid file key format")
        return False

    # Extract elements from the file key
    file_key_elements = extract_file_key_elements(file_key)
    supplier = file_key_elements["supplier"]
    vaccine_type = file_key_elements["vaccine_type"]

    # Validate each file key element
    if not (
        vaccine_type in Constants.VALID_VACCINE_TYPES
        and file_key_elements["vaccination"] == "VACCINATIONS"
        and file_key_elements["version"] in Constants.VALID_VERSIONS
        and supplier  # Note that if supplier could be identified, this also implies that ODS code is valid
        and is_valid_datetime(file_key_elements["timestamp"])
        and file_key_elements["extension"] == "CSV"
    ):
        logger.error("Initial file validation failed: invalid file key")
        return False

    # Validate has permissions for the vaccine type
    if not validate_vaccine_type_permissions(supplier, vaccine_type):
        logger.error("Initial file validation failed: %s does not have permissions for %s", supplier, vaccine_type)
        return False

    return True, get_permissions_config_json_from_cache().get("all_permissions", {}).get(supplier, [])
