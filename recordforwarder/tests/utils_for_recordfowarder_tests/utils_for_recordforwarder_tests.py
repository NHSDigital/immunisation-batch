from unittest.mock import Mock
import requests


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


def create_mock_api_response(status_code: int, diagnostics: str = None) -> requests.Response:
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = status_code
    mock_response.headers = {
        "location": "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api/Immunization/test_id"
    }
    if diagnostics:
        mock_response.json.return_value = create_mock_operation_outcome(diagnostics)
    return mock_response
