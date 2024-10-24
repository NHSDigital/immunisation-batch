"""Function to process a single row of a csv file"""

import json
import logging
from get_imms_id import get_imms_id
from convert_fhir_json import convert_to_fhir_json
from constants import Diagnostics

logger = logging.getLogger()


def process_row(vaccine_type: str, allowed_operations: set, row: dict) -> dict:
    """
    Processes a row of the file and returns a dictionary containing the fhir_json, action_flag, imms_id
    (where applicable), version(where applicable) and any diagnostics.
    """
    action_flag = row.get("ACTION_FLAG", "").upper()
    # Handle invalid action_flag
    if action_flag not in ("NEW", "UPDATE", "DELETE"):
        logger.info("Invalid ACTION_FLAG '%s' - ACTION_FLAG MUST BE 'NEW', 'UPDATE' or 'DELETE'", action_flag)
        return {"diagnostics": Diagnostics.INVALID_ACTION_FLAG}

    operation_requested = action_flag.replace("NEW", "CREATE")
    logger.info("OPERATION REQUESTED:  %s", operation_requested)
    logger.info("OPERATION ALLOWED: %s", allowed_operations)

    # Handle no permissions
    if operation_requested not in allowed_operations:
        logger.info("Skipping row as supplier does not have the permissions for this operation %s", operation_requested)
        return {"diagnostics": Diagnostics.NO_PERMISSIONS}

    # Handle missing UNIQUE_ID or UNIQUE_ID_URI or invalid conversion
    if not ((identifier_system := row.get("UNIQUE_ID_URI")) and (identifier_value := row.get("UNIQUE_ID"))):
        logger.error("Invalid row format: row is missing either UNIQUE_ID or UNIQUE_ID_URI")
        return {"diagnostics": Diagnostics.MISSING_UNIQUE_ID}

    # Obtain the imms id and version from the ieds for update and delete
    imms_id = None
    version = None
    if operation_requested in ("DELETE", "UPDATE"):
        response, status_code = get_imms_id(identifier_system, identifier_value)
        response = json.loads(response)
        # Handle non-200 response from Immunisation API
        if not (response.get("total") == 1 and status_code == 200):
            logger.error("imms_id not found:%s and status_code: %s", response, status_code)
            return {"diagnostics": Diagnostics.UNABLE_TO_OBTAIN_IMMS_ID}
        resource = response.get("entry", [])[0]["resource"]
        # Handle unable to obtain imms id
        if not (imms_id := resource.get("id")):
            return {"diagnostics": Diagnostics.UNABLE_TO_OBTAIN_IMMS_ID}

    # Handle unable to obtain version for UPDATE
    if operation_requested == "UPDATE" and not (version := resource.get("meta", {}).get("versionId")):
        return {"diagnostics": Diagnostics.UNABLE_TO_OBTAIN_VERSION}

    # Convert to JSON
    fhir_json, valid = convert_to_fhir_json(row, vaccine_type)
    # Handle invalid conversion
    if not valid:
        logger.error("Invalid row format: unable to complete conversion")
        return {"diagnostics": Diagnostics.INVALID_CONVERSION}

    # Handle success
    return {
        "fhir_json": fhir_json,
        "operation_requested": operation_requested,
        **({"imms_id": imms_id} if imms_id is not None else {}),
        **({"version": version} if version is not None else {}),
    }
