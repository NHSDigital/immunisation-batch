"""ImmunizationApi class for sending GET request to Imms API to obtain id and version"""

import os
import logging
from errors import IdNotFoundError
from clients import lambda_client
from utils_for_record_forwarder import invoke_lambda
from constants import IMMS_BATCH_APP_NAME

logger = logging.getLogger()


def get_imms_id_and_version(fhir_json: dict) -> tuple[str, int]:
    """Send a GET request to Imms API requesting the id and version"""
    # Create payload
    headers = {"SupplierSystem": IMMS_BATCH_APP_NAME}
    identifier = fhir_json.get("identifier", [{}])[0]
    immunization_identifier = f"{identifier.get('system')}|{identifier.get('value')}"
    query_string_parameters = {"_element": "id,meta", "immunization.identifier": immunization_identifier}
    payload = {"headers": headers, "body": None, "queryStringParameters": query_string_parameters}

    # Invoke lambda
    status_code, body, _ = invoke_lambda(lambda_client, os.getenv("SEARCH_LAMBDA_NAME"), payload)

    # Handle non-200 or empty response
    if not (body.get("total") == 1 and status_code == 200):
        logger.error("imms_id not found:%s and status_code: %s", body, status_code)
        raise IdNotFoundError("Imms id not found")

    # Return imms_id and version
    resource = body.get("entry", [])[0]["resource"]
    return resource.get("id"), resource.get("meta", {}).get("versionId")
