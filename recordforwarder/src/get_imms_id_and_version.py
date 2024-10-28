"""ImmunizationApi class for sending GET request to Imms API to obtain id and version"""

import os
import json
import logging
import boto3
from errors import IdNotFoundError

logger = logging.getLogger()


lambda_client = boto3.client("lambda", region_name="eu-west-2")
search_lambda_name = os.getenv("SEARCH_LAMBDA_NAME")


def get_imms_id_and_version(identifier_system: str, identifier_value: str):
    """Send a GET request to Imms API requesting the id and version"""
    payload = {
        "headers": {"SupplierSystem": "Imms-Batch-App"},
        "body": None,
        "queryStringParameters": {
            "_element": "id,meta",
            "immunization.identifier": f"{identifier_system}|{identifier_value}",
        },
    }
    # Invoke the target Lambda function
    response = lambda_client.invoke(
        FunctionName=search_lambda_name,
        InvocationType="RequestResponse",  # Change to 'Event' for asynchronous invocation
        Payload=json.dumps(payload),
    )
    response_payload = json.loads(response["Payload"].read())
    status_code = response_payload.get("statusCode")
    response = json.loads(response_payload.get("body"))

    if not (response.get("total") == 1 and status_code == 200):
        logger.error("imms_id not found:%s and status_code: %s", response, status_code)
        raise IdNotFoundError("Imms id not found")

    resource = response.get("entry", [])[0]["resource"]

    return resource.get("id"), resource.get("meta", {}).get("versionId")
