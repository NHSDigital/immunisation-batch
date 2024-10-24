"""ImmunizationApi class for sending GET request to Imms API to obtain id and version"""

import os
import json
import boto3


client = boto3.client("lambda", region_name="eu-west-2")
search_lambda_name = os.getenv("SEARCH_IMMS_LAMBDA")


def get_imms_id(identifier_system: str, identifier_value: str):
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
    response = client.invoke(
        FunctionName=search_lambda_name,
        InvocationType="RequestResponse",  # Change to 'Event' for asynchronous invocation
        Payload=json.dumps(payload),
    )
    response_payload = json.loads(response["Payload"].read())
    if response_payload.get("statusCode") != 200:
        return response_payload.get("body"), 500
    else:
        return response_payload.get("body"), 200
