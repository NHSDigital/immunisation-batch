"""Utils for recordforwarder"""

import os
import json


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def invoke_lambda(lambda_client, lambda_name: str, payload: dict) -> tuple[int, dict, str]:
    """
    Uses the lambda_client to invoke the specified lambda with the given payload.
    Returns the ressponse status code, body (loaded in as a dictionary) and headers.
    """
    # Change InvocationType to 'Event' for asynchronous invocation
    response = lambda_client.invoke(
        FunctionName=lambda_name, InvocationType="RequestResponse", Payload=json.dumps(payload)
    )
    response_payload = json.load(response["Payload"])
    body = json.loads(response_payload.get("body", "{}"))
    return response_payload.get("statusCode"), body, response_payload.get("headers")
