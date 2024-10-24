from unittest.mock import MagicMock
import requests
import json


def create_mock_operation_outcome(diagnostics: str) -> dict:
    return json.dumps({
        "resourceType": "OperationOutcome",
        "id": "45b552ca-755a-473f-84df-c7e7767bd2ac",
        "meta": {"profile": ["https://simplifier.net/guide/UKCoreDevelopment2/ProfileUKCore-OperationOutcome"]},
        "issue": [
            {
                "severity": "error",
                "code": "duplicate",
                "details": {
                    "coding": [{"system": "https://fhir.nhs.uk/Codesystem/http-error-codes", "code": "DUPLICATE"}]
                },
                "diagnostics": diagnostics,
            }
        ],
    })


def create_mock_api_response(status_code: int, diagnostics: str = None) -> requests.Response:
    mock_response = MagicMock()
    if diagnostics is None:
        mock_response['Payload'].read.return_value = json.dumps({
                "statusCode": status_code,
                "headers": {
                    "Location": "https://example.com/immunization/test_id"
                }
            })
    if diagnostics:
        mock_response['Payload'].read.return_value = json.dumps({
                    "statusCode": status_code,
                    "body": create_mock_operation_outcome(diagnostics)})

    return mock_response
