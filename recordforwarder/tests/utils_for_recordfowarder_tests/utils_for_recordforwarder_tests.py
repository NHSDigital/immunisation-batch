import json


def create_mock_operation_outcome(diagnostics: str, code: str = "duplicate") -> dict:
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


def generate_payload(status_code: int, headers: dict = {}, body: dict = None):
    return {"statusCode": status_code, **({"body": json.dumps(body)} if body is not None else {}), "headers": headers}


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
