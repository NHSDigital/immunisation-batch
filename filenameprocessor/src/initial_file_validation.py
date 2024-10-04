"""Functions for initial file validation"""

import logging
import os
from re import match
from datetime import datetime
from constants import Constants
from fetch_permissions import get_permissions_config_json_from_s3
from utils_for_filenameprocessor import extract_file_key_elements, get_environment, get_csv_content_dict_reader

logger = logging.getLogger()


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


def validate_content_headers(csv_content_reader):
    """Returns a bool to indicate whether the given CSV headers match the 34 expected headers exactly"""
    return csv_content_reader.fieldnames == Constants.EXPECTED_CSV_HEADERS


def get_supplier_permissions(supplier: str) -> list:
    """
    Returns the permissions for the given supplier. Returns an empty list if the permissions config json could not
    be downloaded, or the supplier has no permissions.
    """
    config_bucket_name = os.getenv("CONFIG_BUCKET_NAME", f"immunisation-batch-{get_environment()}-configs")
    print(config_bucket_name, "CONFIG BUCKET NAME")
    return get_permissions_config_json_from_s3(config_bucket_name).get("all_permissions", {}).get(supplier, [])


def validate_vaccine_type_permissions(supplier: str, vaccine_type: str):
    """Returns True if the given supplier has any permissions for the given vaccine type, else False"""
    allowed_permissions = get_supplier_permissions(supplier)
    return vaccine_type in " ".join(allowed_permissions)


def validate_action_flag_permissions(csv_content_dict_reader, supplier: str, vaccine_type: str) -> bool:
    """
    Returns True if the supplier has permission to perform ANY of the requested actions for the given vaccine type,
    else False.
    """
    # Obtain the allowed permissions for the supplier
    allowed_permissions_set = set(get_supplier_permissions(supplier))

    # If the supplier has full permissions for the vaccine type return True
    if f"{vaccine_type}_FULL" in allowed_permissions_set:
        logger.info("%s has FULL permissions to create, update and delete", supplier)
        return True

    # Extract a list of all unique operation permissions requested in the csv file
    operations_requested = set()
    for row in csv_content_dict_reader:
        action_flag = row.get("ACTION_FLAG", "").upper()
        operations_requested.add("CREATE" if action_flag == "NEW" else action_flag)

    # Check if any of the CSV permissions match the allowed permissions
    operation_requests_set = {f"{vaccine_type}_{operation}" for operation in operations_requested}
    if operation_requests_set.intersection(allowed_permissions_set):
        logger.info(
            "%s permissions %s matches one of the requested permissions required to %s",
            supplier,
            allowed_permissions_set,
            operation_requests_set,
        )
        return True

    return False


def initial_file_validation(file_key: str, bucket_name: str) -> bool:
    """
    Returns True if all elements of file key are valid, content headers are valid and the supplier has the
    appropriate permissions. Else returns False.
    """
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

    # Obtain the file content
    csv_content_dict_reader = get_csv_content_dict_reader(bucket_name=bucket_name, file_key=file_key)

    # Validate the content headers
    if not validate_content_headers(csv_content_dict_reader):
        logger.error("Initial file validation failed: incorrect column headers")
        return False

    # Validate has permissions for the vaccine type
    if not validate_vaccine_type_permissions(supplier, vaccine_type):
        logger.error("Initial file validation failed: %s does not have permissions for %s", supplier, vaccine_type)
        return False

    # Validate has permission to perform at least one of the requested actions
    if not validate_action_flag_permissions(csv_content_dict_reader, supplier, vaccine_type):
        logger.info(
            "Initial file validation failed: %s does not have permissions for any csv ACTION_FLAG operations", supplier
        )
        return False

    return True
