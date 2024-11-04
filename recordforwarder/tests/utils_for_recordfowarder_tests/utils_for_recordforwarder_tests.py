"""Utils for recordfowarder tests"""

import json
import base64
from io import StringIO
from typing import Union


def generate_kinesis_message(message: dict) -> str:
    """Convert a dictionary to a kinesis message"""
    kinesis_encoded_data = base64.b64encode(json.dumps(message).encode("utf-8")).decode("utf-8")
    return {"Records": [{"kinesis": {"data": kinesis_encoded_data}}]}


def generate_mock_operation_outcome(diagnostics: str, code: str = "duplicate") -> dict:
    """Generates an Operation Outcome, with the given diagnostics and code"""
    return {
        "resourceType": "OperationOutcome",
        "id": "an_imms_id",
        "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
        "issue": [
            {
                "severity": "error",
                "code": code,
                "details": {
                    "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": code.upper()}]
                },
                "diagnostics": diagnostics,
            }
        ],
    }


def generate_payload(status_code: int, headers: Union[dict, None] = None, body: dict = None):
    """
    Generates a payload with the given status code, headers and body
    (body is converted to json string, and the key-value pair is omitted if there is no body)
    """
    return {"statusCode": status_code, **({"body": json.dumps(body)} if body is not None else {}), "headers": headers}


def generate_lambda_invocation_side_effect(mock_lambda_payloads):
    """
    Takes a dictionary as input with key-value pairs in the format LAMBDA_TYPE: mock_response_payload, where
    LAMBDA_TYPEs are CREATE, UPDATE, DELETE and SEARCH.
    Returns a function which mocks the side effect of calling lambda_client.invoke on the relevant Imms FHIR API lambda.
    """

    def lambda_invocation_side_effect(FunctionName, *_args, **_kwargs):  # pylint: disable=invalid-name
        for key, value in mock_lambda_payloads.items():
            if FunctionName == f"mock_{key.lower()}_lambda_name":
                response_payload = value
                return {"Payload": StringIO(json.dumps(response_payload))}

    return lambda_invocation_side_effect
