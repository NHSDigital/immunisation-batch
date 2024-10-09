SOURCE_BUCKET_NAME = "immunisation-batch-internal-dev-data-sources"
DESTINATION_BUCKET_NAME = "immunisation-batch-internal-dev-data-destinations"
CONFIG_BUCKET_NAME = "immunisation-batch-internal-dev-configs"
STREAM_NAME = "imms-batch-internal-dev-processingdata-stream"

AWS_REGION = "eu-west-2"

TEST_VACCINE_TYPE = "flu"
TEST_SUPPLIER = "EMIS"
TEST_ODS_CODE = "8HK48"
TEST_MESSAGE_ID = "123456"

TEST_FILE_KEY = f"{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000.csv"
TEST_ACK_FILE_KEY = f"forwardedFile/{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000_response.csv"

# TEST_EVENT_DUMPED = json.dumps(
#     {
#         "message_id": TEST_MESSAGE_ID,
#         "vaccine_type": TEST_VACCINE_TYPE,
#         "supplier": TEST_SUPPLIER,
#         "filename": TEST_FILE_KEY,
#     }
# )

# TEST_EVENT = {
#     "message_id": TEST_MESSAGE_ID,
#     "vaccine_type": TEST_VACCINE_TYPE,
#     "supplier": TEST_SUPPLIER,
#     "filename": TEST_FILE_KEY,
# }

MOCK_ENVIRONMENT_DICT = {
    "ENVIRONMENT": "internal-dev",
    "LOCAL_ACCOUNT_ID": "123456",
    "ACK_BUCKET_NAME": DESTINATION_BUCKET_NAME,
    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
    "KINESIS_STREAM_ARN": f"arn:aws:kinesis:{AWS_REGION}:123456789012:stream/{STREAM_NAME}",
}

test_fhir_json = {
    "resourceType": "Immunization",
    "contained": [
        {
            "resourceType": "Practitioner",
            "id": "Pract1",
            "name": [{"family": "Doe", "given": ["Jane"]}],
        },
        {
            "resourceType": "Patient",
            "id": "Pat1",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": "1234567890",
                }
            ],
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
    "identifier": [
        {
            "system": "https://www.ravs.england.nhs.uk/",
            "value": "0001_TEST_v1_RUN_1_ABCD-123_Dose_seq_01",
        }
    ],
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
    "location": {
        "type": "Location",
        "identifier": {
            "value": "ABCDE",
            "system": "https://fhir.nhs.uk/Id/ods-organization-code",
        },
    },
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
            {
                "system": "http://snomed.info/sct",
                "code": "111111111",
                "display": "Subcutaneous route (qualifier value)",
            }
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
                "identifier": {
                    "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                    "value": "DUMMYORG",
                },
            }
        },
    ],
    "reasonCode": [{"coding": [{"system": "http://snomed.info/sct", "code": "dummy"}]}],
    "protocolApplied": [
        {
            "targetDisease": [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "123456789",
                            "display": "Dummy disease caused by dummy virus",
                        }
                    ]
                }
            ],
            "doseNumberPositiveInt": 1,
        }
    ],
}
