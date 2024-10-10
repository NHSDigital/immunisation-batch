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
    action_flag = action_flag.upper() if (action_flag := row.get("ACTION_FLAG")) is not None else ""
    logger.info("ACTION FLAG PERMISSIONS REQUESTED:  %s", action_flag)
    logger.info("ACTION FLAG PERMISSIONS ALLOWED: %s", permission_operations)

    # Handle no permissions
    if action_flag not in permission_operations:
        logger.info("Skipping row as supplier does not have the permissions for this csv operation %s", action_flag)
        return {"diagnostics": "No permissions for operation"}

    # Handle missing UNIQUE_ID or UNIQUE_ID_URI or invalid conversion
    if not ((identifier_system := row.get("UNIQUE_ID_URI")) and (identifier_value := row.get("UNIQUE_ID"))):
        logger.error("Invalid row format: row is missing either UNIQUE_ID or UNIQUE_ID_URI")
        return {"diagnostics": "Unsupported file type received as an attachment"}

    # Obtain the imms id and version from the ieds for update and delete
    if action_flag in ("DELETE", "UPDATE"):
        response, status_code = immunization_api_instance.get_imms_id(identifier_system, identifier_value)
        # Handle non-200 response from Immunisation API
        if not (response.get("total") == 1 and status_code == 200):
            logger.info("imms_id not found:%s and status_code: %s", response, status_code)
            return {"diagnostics": "Unsupported file type received as an attachment"}

    fhir_json, valid = convert_to_fhir_json(row, vaccine_type)
    # Handle invalid conversion
    if not valid:
        logger.error("Invalid row format: unable to complete conversion")
        return {"diagnostics": "Unsupported file type received as an attachment"}

    # Handle success
    resource = response.get("entry", [])[0]["resource"] if action_flag in ("DELETE", "UPDATE") else None
    return {
        "fhir_json": fhir_json,
        "action_flag": action_flag,
        "imms_id": resource.get("id") if resource else None,
        "version": resource.get("meta", {}).get("versionId") if resource else None,
        "diagnostics": None,
    }
