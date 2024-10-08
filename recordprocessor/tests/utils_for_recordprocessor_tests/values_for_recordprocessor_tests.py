import json

VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE = (
    "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
    "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
    "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
    "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
    "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
    "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
    "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
    "LOCATION_CODE|LOCATION_CODE_TYPE_URI\n"
    '9674963871|"SABINA"|"GREIR"|"20190131"|"2"|"GU14 6TU"|"20240610T183325"|"J82067"|'
    '"https://fhir.nhs.uk/Id/ods-organization-code"|"0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"|'
    '"https://www.ravs.england.nhs.uk/"|"new"|"Ellena"|"O\'Reilly"|"20240609"|"TRUE"|'
    '"1303503001"|"Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"|'
    '1|"42605811000001109"|"Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) '
    '(product)"|"Pfizer"|"RSVTEST"|"20241231"|"368208006"|"Left upper arm structure (body structure)"|'
    '"78421000"|"Intramuscular route (qualifier value)"|"0.5"|"258773002"|"Milliliter (qualifier value)"|"Test"|'
    '"J82067"|"https://fhir.nhs.uk/Id/ods-organization-code"\n'
    '1234567890|"JOHN"|"DOE"|"19801231"|"1"|"AB12 3CD"|"20240611T120000"|"J82068"|'
    '"https://fhir.nhs.uk/Id/ods-organization-code"|"0002_COVID19_v1_DOSE_1"|"https://www.ravs.england.nhs.uk/"|'
    '"update"|"Jane"|"Smith"|"20240610"|"FALSE"|"1324657890"|'
    '"Administration of COVID-19 vaccine product (procedure)"|'
    '1|"1234567890"|'
    '"Comirnaty 0.3ml dose concentrate for dispersion for injection multidose vials (Pfizer/BioNTech) '
    '(product)"|"Pfizer/BioNTech"|"COVIDBATCH"|"20250101"|"368208007"|"Right upper arm structure (body structure)"|'
    '"385219009"|"Intramuscular route (qualifier value)"|'
    '"0.3"|"258773002"|"Milliliter (qualifier value)"|"Routine"|'
    '"J82068"|"https://fhir.nhs.uk/Id/ods-organization-code"'
)

API_RESPONSE_WITH_ID_AND_VERSION = {
    "resourceType": "Bundle",
    "type": "searchset",
    "link": [
        {
            "relation": "self",
            "url": (
                "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
                "Immunization?immunization.identifier=https://supplierABC/identifiers/"
                "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
            ),
        }
    ],
    "entry": [
        {
            "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
            "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
            "resource": {
                "resourceType": "Immunization",
                "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
                "meta": {"versionId": 1},
            },
        }
    ],
    "total": 1,
}, 200

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
TEST_ACK_FILE_KEY = f"processedFile/{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000_response.csv"

TEST_EVENT = json.dumps(
    {
        "message_id": TEST_MESSAGE_ID,
        "vaccine_type": TEST_VACCINE_TYPE,
        "supplier": TEST_SUPPLIER,
        "filename": TEST_FILE_KEY,
    }
)

MOCK_ENVIRONMENT_DICT = {
    "ENVIRONMENT": "internal-dev",
    "LOCAL_ACCOUNT_ID": "123456",
    "ACK_BUCKET_NAME": DESTINATION_BUCKET_NAME,
    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
    "KINESIS_STREAM_ARN": f"arn:aws:kinesis:{AWS_REGION}:123456789012:stream/{STREAM_NAME}",
}

PERMISSIONS_FILE_KEY = "permissions_config.json"

MOCK_PERMISSIONS = {
    "all_permissions": {
        "DPSFULL": ["COVID19_FULL", "FLU_FULL", "MMR_FULL"],
        "DPSREDUCED": ["COVID19_FULL", "FLU_FULL", "MMR_FULL"],
        "EMIS": ["FLU_FULL"],
        "PINNACLE": [""],
        "SONAR": ["FLU_CREATE", "FLU_DELETE"],
        "TPP": [""],
        "AGEM-NIVS": [""],
        "NIMS": [""],
        "EVA": ["COVID19_CREATE", "COVID19_DELETE", "COVID19_UPDATE"],
        "RAVS": [""],
        "MEDICAL_DIRECTOR": [""],
        "WELSH_DA_1": [""],
        "WELSH_DA_2": [""],
        "NORTHERN_IRELAND_DA": [""],
        "SCOTLAND_DA": [""],
        "COVID19_VACCINE_RESOLUTION_SERVICEDESK": [""],
    },
    "definitions:": {
        "_FULL": "Full permissions to create, update and delete a batch record",
        "_CREATE": "Permission to create a batch record",
        "_UPDATE": "Permission to update a batch record",
        "_DELETE": "Permission to delete a batch record",
    },
}
