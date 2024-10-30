from unittest.mock import MagicMock
import requests
import json


def create_mock_operation_outcome(diagnostics: str) -> dict:
    return {
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
    }


response_body_id_and_version_not_found = {
    "resourceType": "Bundle",
    "type": "searchset",
    "link": [
        {
            "relation": "self",
            "url": "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/Immunization?"
            + "immunization.identifier=None&_elements=None",
        }
    ],
    "entry": [],
    "total": 0,
}

response_body_id_and_version_found = {
    "resourceType": "Bundle",
    "type": "searchset",
    "entry": [{"resource": {"id": "277befd9-574e-47fe-a6ee-189858af3bb0", "meta": {"versionId": 2}}}],
    "total": 1,
}


def create_mock_search_lambda_response(
    status_code: int, diagnostics: str = None, id_and_version_found: bool = True
) -> requests.Response:
    """Creates a mock response for a request sent to the search lambda for imms_id and version."""

    body = (
        create_mock_operation_outcome(diagnostics)
        if diagnostics
        else response_body_id_and_version_found if id_and_version_found else response_body_id_and_version_not_found
    )

    mock_response = MagicMock()
    mock_response["Payload"].read.return_value = json.dumps(
        {
            "statusCode": status_code,
            "headers": {"Location": "https://example.com/immunization/test_id"},
            **({"body": json.dumps(body)} if body is not None else {}),
        }
    )

    return mock_response
