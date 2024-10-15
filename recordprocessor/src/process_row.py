"""Function to process a single row of a csv file"""

import logging
from models.cache import Cache
from models.authentication import AppRestrictedAuth, Service
from get_imms_id import ImmunizationApi
from convert_fhir_json import convert_to_fhir_json

cache = Cache("/tmp")
authenticator = AppRestrictedAuth(service=Service.IMMUNIZATION, cache=cache)
immunization_api_instance = ImmunizationApi(authenticator)
logger = logging.getLogger()


def process_row(vaccine_type: str, permission_operations: set, row: dict) -> dict:
    """
    Processes a row of the file and returns a dictionary containing the fhir_json, action_flag, imms_id
    (where applicable), version(where applicable) and any diagnostics.
    """
    action_flag = row.get("ACTION_FLAG")
    operation_requested = action_flag.upper().replace("NEW", "CREATE") if action_flag is not None else ""
    logger.info("OPERATION REQUESTED:  %s", operation_requested)
    logger.info("OPERATION ALLOWED: %s", permission_operations)

    # Handle no permissions
    if operation_requested not in permission_operations:
        logger.info("Skipping row as supplier does not have the permissions for this operation %s", operation_requested)
        return {"diagnostics": "No permissions for operation"}

    # Handle missing UNIQUE_ID or UNIQUE_ID_URI or invalid conversion
    if not ((identifier_system := row.get("UNIQUE_ID_URI")) and (identifier_value := row.get("UNIQUE_ID"))):
        logger.error("Invalid row format: row is missing either UNIQUE_ID or UNIQUE_ID_URI")
        return {"diagnostics": "Unsupported file type received as an attachment"}

    # Obtain the imms id and version from the ieds for update and delete
    imms_id = None
    version = None
    if operation_requested in ("DELETE", "UPDATE"):
        response, status_code = immunization_api_instance.get_imms_id(identifier_system, identifier_value)
        # Handle non-200 response from Immunisation API
        if not (response.get("total") == 1 and status_code == 200):
            logger.info("imms_id not found:%s and status_code: %s", response, status_code)
            return {"diagnostics": "Unsupported file type received as an attachment"}
        resource = response.get("entry", [])[0]["resource"]
        if not (imms_id := resource.get("id")):
            return {"diagnostics": "Unable to obtain imms_id"}
        if operation_requested == "UPDATE" and not (version := resource.get("meta", {}).get("versionId")):
            return {"diagnostics": "Unable to obtain version"}

    # Convert to JSON
    fhir_json, valid = convert_to_fhir_json(row, vaccine_type)
    # Handle invalid conversion
    if not valid:
        logger.error("Invalid row format: unable to complete conversion")
        return {"diagnostics": "Unsupported file type received as an attachment"}

    # Handle success
    return {
        "fhir_json": fhir_json,
        "operation_requested": operation_requested,
        **({"imms_id": imms_id} if imms_id is not None else {}),
        **({"version": version} if version is not None else {}),
    }
