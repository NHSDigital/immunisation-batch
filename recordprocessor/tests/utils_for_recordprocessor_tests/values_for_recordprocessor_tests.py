"""Values for use in tests"""

import json
from copy import deepcopy

TEST_UNIQUE_ID = "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"
TEST_DATE = "20240609"

FILE_HEADERS = (
    "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
    "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
    "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
    "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
    "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
    "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
    "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
    "LOCATION_CODE|LOCATION_CODE_TYPE_URI"
)

FILE_ROW_NEW = (
    '9674963871|"SABINA"|"GREIR"|"20190131"|"2"|"GU14 6TU"|"20240610T183325"|"J82067"|'
    f'"https://fhir.nhs.uk/Id/ods-organization-code"|"{TEST_UNIQUE_ID}"|'
    f'"https://www.ravs.england.nhs.uk/"|"new"|"Ellena"|"O\'Reilly"|"{TEST_DATE}"|"TRUE"|'
    '"1303503001"|"Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"|'
    '1|"42605811000001109"|"Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) '
    '(product)"|"Pfizer"|"RSVTEST"|"20241231"|"368208006"|"Left upper arm structure (body structure)"|'
    '"78421000"|"Intramuscular route (qualifier value)"|"0.5"|"258773002"|"Milliliter (qualifier value)"|"Test"|'
    '"J82067"|"https://fhir.nhs.uk/Id/ods-organization-code"'
)

FILE_ROW_UPDATE = (
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

FILE_ROW_DELETE = (
    '1234567890|"JOHN"|"DOE"|"19801231"|"1"|"AB12 3CD"|"20240611T120000"|"J82068"|'
    '"https://fhir.nhs.uk/Id/ods-organization-code"|"0002_COVID19_v1_DOSE_1"|"https://www.ravs.england.nhs.uk/"|'
    '"delete"|"Jane"|"Smith"|"20240610"|"FALSE"|"1324657890"|'
    '"Administration of COVID-19 vaccine product (procedure)"|'
    '1|"1234567890"|'
    '"Comirnaty 0.3ml dose concentrate for dispersion for injection multidose vials (Pfizer/BioNTech) '
    '(product)"|"Pfizer/BioNTech"|"COVIDBATCH"|"20250101"|"368208007"|"Right upper arm structure (body structure)"|'
    '"385219009"|"Intramuscular route (qualifier value)"|'
    '"0.3"|"258773002"|"Milliliter (qualifier value)"|"Routine"|'
    '"J82068"|"https://fhir.nhs.uk/Id/ods-organization-code"'
)

VALID_FILE_CONTENT_WITH_NEW = FILE_HEADERS + "\n" + FILE_ROW_NEW
VALID_FILE_CONTENT_WITH_UPDATE = FILE_HEADERS + "\n" + FILE_ROW_UPDATE
VALID_FILE_CONTENT_WITH_DELETE = FILE_HEADERS + "\n" + FILE_ROW_DELETE
VALID_FILE_CONTENT_WITH_UPDATE_AND_DELETE = FILE_HEADERS + "\n" + FILE_ROW_UPDATE + "\n" + FILE_ROW_DELETE
VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE = FILE_HEADERS + "\n" + FILE_ROW_NEW + "\n" + FILE_ROW_UPDATE
VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE_AND_DELETE = (
    FILE_HEADERS + "\n" + FILE_ROW_NEW + "\n" + FILE_ROW_UPDATE + "\n" + FILE_ROW_DELETE
)

TEST_ID = "277befd9-574e-47fe-a6ee-189858af3bb0"
TEST_VERSION = 2


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
                "id": TEST_ID,
                "meta": {"versionId": TEST_VERSION},
            },
        }
    ],
    "total": 1,
}, 200

API_RESPONSE_WITHOUT_ID_AND_VERSION = {
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
            "resource": {"resourceType": "Immunization"},
        }
    ],
    "total": 1,
}, 200


API_RESPONSE_WITHOUT_VERSION = {
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
            "resource": {"resourceType": "Immunization", "id": TEST_ID},
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
TEST_FILE_ID = "123456"
TEST_PERMISSION = ["COVID19_FULL", "FLU_FULL", "MMR_FULL"]

TEST_FILE_KEY = f"{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000.csv"
TEST_ACK_FILE_KEY = f"processedFile/{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000_response.csv"

TEST_EVENT_DUMPED = json.dumps(
    {
        "message_id": TEST_FILE_ID,
        "vaccine_type": TEST_VACCINE_TYPE,
        "supplier": TEST_SUPPLIER,
        "filename": TEST_FILE_KEY,
        "permission": TEST_PERMISSION,
    }
)

TEST_EVENT = {
    "message_id": TEST_FILE_ID,
    "vaccine_type": TEST_VACCINE_TYPE,
    "supplier": TEST_SUPPLIER,
    "filename": TEST_FILE_KEY,
}

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
        "DPSFULL": ["COVID19_FULL", "FLU_FULL", "MMR_FULL", "RSV_FULL"],
        "DPSREDUCED": ["COVID19_FULL", "FLU_FULL", "MMR_FULL", "RSV_FULL"],
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


TEST_PERMISSIONS_CONFIG = {
    "all_permissions": {
        "DPFULL": ["COVID19_FULL", "FLU_FULL", "MMR_FULL", "RSV_FULL"],
        "DPREDUCED": ["COVID19_FULL", "FLU_FULL", "MMR_FULL", "RSV_FULL"],
        "SUPPLIER1": ["COVID19_CREATE", "COVID19_DELETE", "COVID19_UPDATE"],
        "SUPPLIER2": ["RSV_UPDATE"],
        "EMIS": ["FLU_CREATE", "FLU_DELETE"],
        "SUPPLIER4": [""],
    },
    "definitions:": {
        "_FULL": "Full permissions to create, update and delete a batch record",
        "_CREATE": "Permission to create a batch record",
        "_UPDATE": "Permission to update a batch record",
        "_DELETE": "Permission to delete a batch record",
    },
}


# ---------------------------------------------------------------------------------------------------------------------
# Prepare mock requests

mandatory_fields = {
    "PERSON_FORENAME": "PHYLIS",
    "PERSON_SURNAME": "PEEL",
    "PERSON_DOB": "20080217",
    "PERSON_GENDER_CODE": "0",
    "PERSON_POSTCODE": "WD25 0DZ",
    "DATE_AND_TIME": "20240904T183325",
    "SITE_CODE": "RVVKC",
    "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
    "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
    "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
    "ACTION_FLAG": "update",
    "RECORDED_DATE": "20240904",
    "PRIMARY_SOURCE": "TRUE",
    "VACCINATION_PROCEDURE_CODE": "956951000000104",
    "LOCATION_CODE": "RJC02",
    "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
}

non_mandatory_fields = {
    "NHS_NUMBER": "9732928395",
    "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
    "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
    "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
    "DOSE_SEQUENCE": "1",
    "VACCINE_PRODUCT_CODE": "42223111000001107",
    "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
    "VACCINE_MANUFACTURER": "Sanofi Pasteur",
    "BATCH_NUMBER": "BN92478105653",
    "EXPIRY_DATE": "20240915",
    "SITE_OF_VACCINATION_CODE": "368209003",
    "SITE_OF_VACCINATION_TERM": "Right arm",
    "ROUTE_OF_VACCINATION_CODE": "1210999013",
    "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
    "DOSE_AMOUNT": "0.3",
    "DOSE_UNIT_CODE": "2622896019",
    "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
    "INDICATION_CODE": "1037351000000105",
}

all_fields = {**mandatory_fields, **non_mandatory_fields}
mandatory_fields_only = {**mandatory_fields, **{k: "" for k in non_mandatory_fields}}

# Requests (format is dictionary)
update_request = deepcopy(all_fields)

create_request = deepcopy(all_fields)
create_request["ACTION_FLAG"] = "new"

update_request_action_flag_missing = deepcopy(all_fields)
update_request_action_flag_missing["ACTION_FLAG"] = ""

update_request_unique_id_missing = deepcopy(all_fields)
update_request_unique_id_missing["UNIQUE_ID"] = ""

update_request_unique_id_uri_missing = deepcopy(all_fields)
update_request_unique_id_uri_missing["UNIQUE_ID_URI"] = ""

update_request_dose_sequence_missing = deepcopy(all_fields)
update_request_dose_sequence_missing["DOSE_SEQUENCE"] = ""

update_request_dose_sequence_string = deepcopy(all_fields)
update_request_dose_sequence_string["DOSE_SEQUENCE"] = "test"

# Mock requests (format is list of dictionaries)
mock_update_request = [update_request]

mock_request_dose_sequence_string = [update_request_dose_sequence_string]

mock_request_dose_sequence_missing = [update_request_dose_sequence_missing]

mock_request_only_mandatory = [deepcopy(mandatory_fields_only)]

mock_request_params_missing = [
    update_request_action_flag_missing,
    update_request_unique_id_missing,
    update_request_unique_id_uri_missing,
    create_request,
]


class TestValues:
    """Mock requests for use in tests"""

    # Requests (format is dictionary)
    update_request = update_request
    create_request = create_request
    update_request_unique_id_missing = update_request_unique_id_missing
    update_request_dose_sequence_missing = update_request_dose_sequence_missing
    update_request_dose_sequence_string = update_request_dose_sequence_string

    # Mock requests (format is list of dictionaries)
    mock_update_request = mock_update_request
    mock_request_dose_sequence_string = mock_request_dose_sequence_string
    mock_request_dose_sequence_missing = mock_request_dose_sequence_missing
    mock_request_only_mandatory = mock_request_only_mandatory
    mock_request_params_missing = mock_request_params_missing


mock_disease_codes = {
    "covid_19": "840539006",
    "flu": "6142004",
    "measles": "14189004",
    "mumps": "36989005",
    "rubella": "36653000",
    "rsv": "55735004",
}

mock_disease_display_terms = {
    "covid_19": "Disease caused by severe acute respiratory syndrome coronavirus 2",
    "flu": "Influenza",
    "measles": "Measles",
    "mumps": "Mumps",
    "rubella": "Rubella",
    "rsv": "Respiratory syncytial virus infection (disorder)",
}

MOCK_VACCINE_DISEASE_MAPPING = {
    "covid19": ["covid_19"],
    "flu": ["flu"],
    "mmr": ["measles", "mumps", "rubella"],
    "rsv": ["rsv"],
}

TARGET_DISEASE_ELEMENTS = {
    "RSV": [
        {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "55735004",
                    "display": "Respiratory syncytial virus infection (disorder)",
                }
            ]
        }
    ],
}
