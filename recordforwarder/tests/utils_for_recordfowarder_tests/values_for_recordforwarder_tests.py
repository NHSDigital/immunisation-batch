"""Values for use in recordforwarder tests"""

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


test_fhir_json = {
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
    "identifier": [{"system": Urls.RAVS, "value": "0001_TEST_v1_RUN_1_ABCD-123_Dose_seq_01"}],
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


class Message:
    """Class containing example kinesis messages"""

    ROW_ID = "123456"
    IMMS_ID = "277befd9-574e-47fe-a6ee-189858af3bb0"
    DIAGNOSTICS = Diagnostics.MISSING_UNIQUE_ID
    base_message_fields = {"row_id": ROW_ID, "file_key": TestFile.FILE_KEY, "supplier": TestFile.SUPPLIER}
    create_message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "CREATE"}
    update_message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "UPDATE"}
    delete_message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "DELETE"}
    diagnostics_message = {**base_message_fields, "diagnostics": DIAGNOSTICS}


lambda_success_headers = {"Location": "https://example.com/immunization/test_id"}


class ResponseBody:
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
