"""Utils for recordforwarder"""

import os
import json
from errors import MessageNotSuccessfulError


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def extract_file_key_elements(file_key: str) -> dict:
    """
    Returns a dictionary containing each of the elements which can be extracted from the file key.
    All elements are converted to upper case.\n
    """
    file_key = file_key.upper()
    file_key_parts_without_extension = file_key.split(".")[0].split("_")
    file_key_elements = {"vaccine_type": file_key_parts_without_extension[0]}
    return file_key_elements


def get_operation_outcome_diagnostics(body: dict) -> str:
    """
    Returns the diagnostics from the API response. If the diagnostics can't be found in the API response,
    returns a default diagnostics string
    """
    try:
        return body.get("issue")[0].get("diagnostics")
    except (AttributeError, IndexError):
        return "Unable to obtain diagnostics from API response"


def invoke_lambda(lambda_client, lambda_name: str, payload: dict) -> tuple[int, dict, str]:
    """
    Uses the lambda_client to invoke the specified lambda with the given payload.
    Returns the ressponse status code, body (loaded in as a dictionary) and headers.
    """
    # Change InvocationType to 'Event' for asynchronous invocation
    if ("search_imms" in lambda_name):
        response = lambda_client.invoke(
            FunctionName=lambda_name, InvocationType="RequestResponse", Payload=json.dumps(payload)
        )
        response_payload = json.loads(response["Payload"].read())
        body = json.loads(response_payload.get("body", "{}"))
        return response_payload.get("statusCode"), body, response_payload.get("headers")
    else:
        response = lambda_client.invoke(
            FunctionName=lambda_name, InvocationType="Event", Payload=json.dumps(payload)
        )
        body = json.loads(response.get("body", "{}"))
        if response["statusCode"] != "200":
            raise MessageNotSuccessfulError(get_operation_outcome_diagnostics(body))
        else:
            return "200", None, None
