"""Values for use in recordforwarder tests"""

SOURCE_BUCKET_NAME = "immunisation-batch-internal-dev-data-sources"
DESTINATION_BUCKET_NAME = "immunisation-batch-internal-dev-data-destinations"

AWS_REGION = "eu-west-2"

TEST_VACCINE_TYPE = "flu"
TEST_SUPPLIER = "EMIS"
TEST_ODS_CODE = "8HK48"
TEST_ROW_ID = "123456"
TEST_IMMS_ID = "imms_6543219"

TEST_FILE_KEY = f"{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000.csv"
TEST_ACK_FILE_KEY = f"forwardedFile/{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000_BusAck.csv"

base_message_fields = {"row_id": TEST_ROW_ID, "file_key": TEST_FILE_KEY, "supplier": TEST_SUPPLIER}
lambda_success_headers = {"Location": "https://example.com/immunization/test_id"}

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

test_fhir_json = {
    "resourceType": "Immunization",
    "contained": [
        {"resourceType": "Practitioner", "id": "Pract1", "name": [{"family": "Doe", "given": ["Jane"]}]},
        {
            "resourceType": "Patient",
            "id": "Pat1",
            "identifier": [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": "1234567890"}],
            "name": [{"family": "SMITH", "given": ["JOHN"]}],
            "gender": "male",
            "birthDate": "2000-01-01",
            "address": [{"postalCode": "AB12 3CD"}],
        },
    ],
    "extension": [
        {
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "123456789",
                        "display": "Administration of vaccine product containing only Dummy antigen (procedure)",
                    }
                ]
            },
        }
    ],
    "identifier": [{"system": "https://www.ravs.england.nhs.uk/", "value": "0001_TEST_v1_RUN_1_ABCD-123_Dose_seq_01"}],
    "status": "completed",
    "vaccineCode": {
        "coding": [
            {
                "system": "http://snomed.info/sct",
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
    "location": {"identifier": {"value": "ABCDE", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}},
    "lotNumber": "DUMMYLOT",
    "expirationDate": "2024-12-31",
    "site": {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "code": "999999999",
                "display": "Right upper arm structure (body structure)",
            }
        ]
    },
    "route": {
        "coding": [
            {"system": "http://snomed.info/sct", "code": "111111111", "display": "Subcutaneous route (qualifier value)"}
        ]
    },
    "doseQuantity": {
        "system": "http://snomed.info/sct",
        "value": 0.5,
        "unit": "Milliliter (qualifier value)",
        "code": "123456789",
    },
    "performer": [
        {"actor": {"reference": "#Pract1"}},
        {
            "actor": {
                "type": "Organization",
                "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "DUMMYORG"},
            }
        },
    ],
    "reasonCode": [{"coding": [{"system": "http://snomed.info/sct", "code": "dummy"}]}],
    "protocolApplied": [
        {
            "targetDisease": [
                {"coding": [{"system": "http://snomed.info/sct", "code": "123456789", "display": "Dummy disease"}]}
            ],
            "doseNumberPositiveInt": 1,
        }
    ],
}

test_fixed_time_taken = [
    1000000.0,
    1000001.0,
    1000001.0,
    1000000.0,
    1000001.0,
    1000001.0,
    1000000.0,
    1000001.0,
    1000001.0,
]


class Diagnostics:
    """Diagnostics messages"""

    INVALID_ACTION_FLAG = "Invalid ACTION_FLAG - ACTION_FLAG must be 'NEW', 'UPDATE' or 'DELETE'"
    NO_PERMISSIONS = "No permissions for requested operation"
    MISSING_UNIQUE_ID = "UNIQUE_ID or UNIQUE_ID_URI is missing"
    UNABLE_TO_OBTAIN_IMMS_ID = "Unable to obtain imms event id"
    UNABLE_TO_OBTAIN_VERSION = "Unable to obtain current imms event version"
    INVALID_CONVERSION = "Unable to convert row to FHIR Immunization Resource JSON format"
