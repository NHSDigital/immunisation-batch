"""Values for use in recordforwarder tests"""

from constants import Operations
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    generate_lambda_payload,
    generate_operation_outcome,
)

MOCK_ENVIRONMENT_DICT = {
    "SOURCE_BUCKET_NAME": "immunisation-batch-internal-dev-data-sources",
    "ACK_BUCKET_NAME": "immunisation-batch-internal-dev-data-destinations",
    "ENVIRONMENT": "internal-dev",
    "LOCAL_ACCOUNT_ID": "123456789012",
    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
    "CREATE_LAMBDA_NAME": "mock_create_lambda_name",
    "UPDATE_LAMBDA_NAME": "mock_update_lambda_name",
    "DELETE_LAMBDA_NAME": "mock_delete_lambda_name",
    "SEARCH_LAMBDA_NAME": "mock_search_lambda_name",
}

SOURCE_BUCKET_NAME = "immunisation-batch-internal-dev-data-sources"
DESTINATION_BUCKET_NAME = "immunisation-batch-internal-dev-data-destinations"

AWS_REGION = "eu-west-2"


class TestFile:
    """Class containing a test file, it's constituent variables and its corresponding ack file"""

    VACCINE_TYPE = "flu"
    SUPPLIER = "EMIS"
    ODS_CODE = "8HK48"

    FILE_KEY = f"{VACCINE_TYPE}_Vaccinations_v5_{ODS_CODE}_20210730T12000000.csv"
    ACK_FILE_KEY = f"forwardedFile/{FILE_KEY.split('.')[0]}_BusAck.csv"


class Urls:
    """Urls for use within FHIR Immunization Resource json"""

    SNOMED = "http://snomed.info/sct"
    NHS_NUMBER = "https://fhir.nhs.uk/Id/nhs-number"
    VACCINATION_PROCEDURE = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
    RAVS = "https://www.ravs.england.nhs.uk/"
    ODS = "https://fhir.nhs.uk/Id/ods-organization-code"


MOCK_IDENTIFIER_SYSTEM = Urls.RAVS
MOCK_IDENTIFIER_VALUE = "Vacc1"


test_imms_fhir_json = {
    "resourceType": "Immunization",
    "contained": [
        {"resourceType": "Practitioner", "id": "Pract1", "name": [{"family": "Doe", "given": ["Jane"]}]},
        {
            "resourceType": "Patient",
            "id": "Pat1",
            "identifier": [{"system": Urls.NHS_NUMBER, "value": "1234567890"}],
            "name": [{"family": "SMITH", "given": ["JOHN"]}],
            "gender": "male",
            "birthDate": "2000-01-01",
            "address": [{"postalCode": "AB12 3CD"}],
        },
    ],
    "extension": [
        {
            "url": Urls.VACCINATION_PROCEDURE,
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": Urls.SNOMED,
                        "code": "123456789",
                        "display": "Administration of vaccine product containing only Dummy antigen (procedure)",
                    }
                ]
            },
        }
    ],
    "identifier": [{"system": MOCK_IDENTIFIER_SYSTEM, "value": MOCK_IDENTIFIER_VALUE}],
    "status": "completed",
    "vaccineCode": {
        "coding": [
            {
                "system": Urls.SNOMED,
                "code": "987654321",
                "display": "Dummy vaccine powder and solvent for solution (product)",
            }
        ]
    },
    "patient": {"reference": "#Pat1"},
    "occurrenceDateTime": "2024-01-01T00:00:00+00:00",
    "recorded": "2024-01-01T00:00:00+00:00",
    "primarySource": True,
    "manufacturer": {"display": "Dummy Pharma"},
    "location": {"identifier": {"value": "ABCDE", "system": Urls.ODS}},
    "lotNumber": "DUMMYLOT",
    "expirationDate": "2024-12-31",
    "site": {
        "coding": [
            {"system": Urls.SNOMED, "code": "999999999", "display": "Right upper arm structure (body structure)"}
        ]
    },
    "route": {
        "coding": [{"system": Urls.SNOMED, "code": "111111111", "display": "Subcutaneous route (qualifier value)"}]
    },
    "doseQuantity": {"system": Urls.SNOMED, "value": 0.5, "unit": "Milliliter (qualifier value)", "code": "123456789"},
    "performer": [
        {"actor": {"reference": "#Pract1"}},
        {
            "actor": {
                "type": "Organization",
                "identifier": {"system": Urls.ODS, "value": "DUMMYORG"},
            }
        },
    ],
    "reasonCode": [{"coding": [{"system": Urls.SNOMED, "code": "dummy"}]}],
    "protocolApplied": [
        {
            "targetDisease": [{"coding": [{"system": Urls.SNOMED, "code": "123456789", "display": "Dummy disease"}]}],
            "doseNumberPositiveInt": 1,
        }
    ],
}


class Diagnostics:
    """Diagnostics messages"""

    INVALID_ACTION_FLAG = "Invalid ACTION_FLAG - ACTION_FLAG must be 'NEW', 'UPDATE' or 'DELETE'"
    NO_PERMISSIONS = "No permissions for requested operation"
    MISSING_UNIQUE_ID = "UNIQUE_ID or UNIQUE_ID_URI is missing"
    UNABLE_TO_OBTAIN_IMMS_ID = "Unable to obtain imms event id"
    UNABLE_TO_OBTAIN_VERSION = "Unable to obtain current imms event version"
    INVALID_CONVERSION = "Unable to convert row to FHIR Immunization Resource JSON format"
    DUPLICATE = f"The provided identifier: {MOCK_IDENTIFIER_SYSTEM}#{MOCK_IDENTIFIER_VALUE} is duplicated"
    MISSING_EVENT_ID = "the provided event ID is either missing or not in the expected format."
    VALIDATION_ERROR = (
        "Validation errors: The provided immunization id:test_id doesn't match with the content of the request body"
    )


class Message:
    """Class containing example kinesis messages"""

    ROW_ID = "123456"
    IMMS_ID = "277befd9-574e-47fe-a6ee-189858af3bb0"
    DIAGNOSTICS = Diagnostics.MISSING_UNIQUE_ID
    base_message_fields = {"row_id": ROW_ID, "file_key": TestFile.FILE_KEY, "supplier": TestFile.SUPPLIER}
    create_message = {**base_message_fields, "fhir_json": test_imms_fhir_json, "operation_requested": Operations.CREATE}
    update_message = {**base_message_fields, "fhir_json": test_imms_fhir_json, "operation_requested": Operations.UPDATE}
    delete_message = {**base_message_fields, "fhir_json": test_imms_fhir_json, "operation_requested": Operations.DELETE}
    diagnostics_message = {**base_message_fields, "diagnostics": DIAGNOSTICS}


lambda_success_headers = {"Location": "https://example.com/immunization/test_id"}


class SearchLambdaResponseBody:
    """Examples of response body for get_imms_id_and_version"""

    id_and_version_not_found = {
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

    id_and_version_found = {
        "resourceType": "Bundle",
        "type": "searchset",
        "entry": [{"resource": {"id": Message.IMMS_ID, "meta": {"versionId": 2}}}],
        "total": 1,
    }


class LambdaPayloads:
    """
    Class containing dictionaries of mock lambda payloads, to be used as inputs for the
    generate_lambda_invocation_side_effect fucntion
    """

    class CREATE:
        """LambdaPayloads for the CREATE lambda"""

        SUCCESS = {Operations.CREATE: generate_lambda_payload(status_code=201, headers=lambda_success_headers)}

        DUPLICATE = {
            Operations.CREATE: generate_lambda_payload(
                status_code=422, body=generate_operation_outcome(diagnostics=Diagnostics.DUPLICATE, code="duplicate")
            )
        }

    class UPDATE:
        """LambdaPayloads for the UPDATE lambda"""

        SUCCESS = {Operations.UPDATE: generate_lambda_payload(status_code=200)}

        MISSING_EVENT_ID = {
            Operations.UPDATE: generate_lambda_payload(
                400, body=generate_operation_outcome(Diagnostics.MISSING_EVENT_ID)
            )
        }

        VALIDATION_ERROR = {
            Operations.UPDATE: generate_lambda_payload(
                status_code=422, body=generate_operation_outcome(Diagnostics.VALIDATION_ERROR)
            )
        }

    class DELETE:
        """LambdaPayloads for the DELETE lambda"""

        SUCCESS = {Operations.DELETE: generate_lambda_payload(status_code=204)}

    class SEARCH:
        """LambdaPayloads for the SEARCH lambda"""

        ID_AND_VERSION_FOUND = {
            Operations.SEARCH: generate_lambda_payload(
                status_code=200, body=SearchLambdaResponseBody.id_and_version_found
            )
        }

        ID_AND_VERSION_NOT_FOUND = {
            Operations.SEARCH: generate_lambda_payload(
                status_code=200, body=SearchLambdaResponseBody.id_and_version_not_found
            )
        }

        FAILURE = {
            Operations.SEARCH: generate_lambda_payload(
                status_code=404, body=generate_operation_outcome("some_diagnostics")
            )
        }

    SUCCESS = {**CREATE.SUCCESS, **UPDATE.SUCCESS, **DELETE.SUCCESS, **SEARCH.ID_AND_VERSION_FOUND}
