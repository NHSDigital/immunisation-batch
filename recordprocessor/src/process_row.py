"""Function to process a single row of a csv file"""

import logging
from convert_to_fhir_imms_resource import convert_to_fhir_imms_resource
from constants import Diagnostics
from mappings import Vaccine

logger = logging.getLogger()


def process_row(vaccine: Vaccine, allowed_operations: set, row: dict) -> dict:
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

    # Handle missing UNIQUE_ID or UNIQUE_ID_URI
    if not (row.get("UNIQUE_ID_URI") and row.get("UNIQUE_ID")):
        logger.error("Invalid row format: row is missing either UNIQUE_ID or UNIQUE_ID_URI")
        return {"diagnostics": Diagnostics.MISSING_UNIQUE_ID}

    # Handle success
    return {"fhir_json": convert_to_fhir_imms_resource(row, vaccine), "operation_requested": operation_requested}
