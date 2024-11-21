"""Values for use in tests"""

import json
from copy import deepcopy
from unittest.mock import MagicMock
from decimal import Decimal
import requests
from src.constants import Urls
from src.mappings import Vaccine
from datetime import datetime

# TARGET_DISEASE_ELEMENTS values are intentionally hard-coded for testing purposes.
TARGET_DISEASE_ELEMENTS = {
    "RSV": [
        {
            "coding": [
                {
                    "system": Urls.SNOMED,
                    "code": "55735004",
                    "display": "Respiratory syncytial virus infection (disorder)",
                }
            ]
        }
    ],
    "COVID19": [
        {
            "coding": [
                {
                    "system": Urls.SNOMED,
                    "code": "840539006",
                    "display": "Disease caused by severe acute respiratory syndrome coronavirus 2",
                }
            ]
        }
    ],
    "FLU": [{"coding": [{"system": Urls.SNOMED, "code": "6142004", "display": "Influenza"}]}],
    "MMR": [
        {"coding": [{"system": Urls.SNOMED, "code": "14189004", "display": "Measles"}]},
        {"coding": [{"system": Urls.SNOMED, "code": "36989005", "display": "Mumps"}]},
        {"coding": [{"system": Urls.SNOMED, "code": "36653000", "display": "Rubella"}]},
    ],
}


TEST_UNIQUE_ID = "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"
TEST_DATE = "20240609"
TEST_UNIQUE_ID_URI = "https://www.ravs.england.nhs.uk/"
TEST_LOCAL_ID_002COVID = f"0002_COVID19_v1_DOSE_1^{TEST_UNIQUE_ID_URI}"
TEST_LOCAL_ID_001RSV = f"0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1^{TEST_UNIQUE_ID_URI}"
TEST_LOCAL_ID_mandatory = f"0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057^{TEST_UNIQUE_ID_URI}"


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
VALID_FILE_CONTENT = (
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

TEST_VACCINE_TYPE = "rsv"
TEST_SUPPLIER = "EMIS"
TEST_ODS_CODE = "8HK48"
TEST_FILE_ID = "123456"
TEST_PERMISSION = ["COVID19_FULL", "FLU_FULL", "MMR_FULL", "RSV_FULL"]
STATIC_DATETIME = datetime(2021, 11, 20, 12, 0, 0)
# For test purposes static time with no seconds
STATIC_ISO_DATETIME = STATIC_DATETIME.replace(second=0, microsecond=0).isoformat(timespec="milliseconds")

TEST_FILE_KEY = f"{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000.csv"
TEST_ACK_FILE_KEY = f"processedFile/{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000_response.csv"
TEST_INF_ACK_FILE_KEY = (
    f"ack/{TEST_VACCINE_TYPE}_Vaccinations_v5_{TEST_ODS_CODE}_20210730T12000000_InfAck_{STATIC_ISO_DATETIME}.csv"
)
TEST_UNIQUE_ID_URI = "https://www.ravs.england.nhs.uk/"
TEST_LOCAL_ID = f"0002_COVID19_v1_DOSE_1^{TEST_UNIQUE_ID_URI}"


TEST_EVENT_DUMPED = json.dumps(
    {
        "message_id": TEST_FILE_ID,
        "vaccine_type": TEST_VACCINE_TYPE,
        "supplier": TEST_SUPPLIER,
        "filename": TEST_FILE_KEY,
        "permission": TEST_PERMISSION,
        "created_at_formatted_string": "2020-01-01",
        "local_id": TEST_LOCAL_ID,
    }
)

TEST_EVENT = {
    "message_id": TEST_FILE_ID,
    "vaccine_type": TEST_VACCINE_TYPE,
    "supplier": TEST_SUPPLIER,
    "filename": TEST_FILE_KEY,
    "permission": TEST_PERMISSION,
    "local_id": TEST_LOCAL_ID,
}

TEST_EVENT_PERMISSION = {
    "message_id": TEST_FILE_ID,
    "vaccine_type": TEST_VACCINE_TYPE,
    "supplier": TEST_SUPPLIER,
    "filename": TEST_FILE_KEY,
    "permission": ["RSV_DELETE"],
}

MOCK_ENVIRONMENT_DICT = {
    "ENVIRONMENT": "internal-dev",
    "LOCAL_ACCOUNT_ID": "123456789012",
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

# Given dictionaries
mandatory_fields = {
    "PERSON_FORENAME": "PHYLIS",
    "PERSON_SURNAME": "PEEL",
    "PERSON_DOB": "20080217",
    "PERSON_GENDER_CODE": "1",
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

critical_fields = {"ACTION_FLAG": "NEW", "UNIQUE_ID": "a_unique_id", "UNIQUE_ID_URI": "a_unique_id_uri"}

# Required field order
field_order = [
    "NHS_NUMBER",
    "PERSON_FORENAME",
    "PERSON_SURNAME",
    "PERSON_DOB",
    "PERSON_GENDER_CODE",
    "PERSON_POSTCODE",
    "DATE_AND_TIME",
    "SITE_CODE",
    "SITE_CODE_TYPE_URI",
    "UNIQUE_ID",
    "UNIQUE_ID_URI",
    "ACTION_FLAG",
    "PERFORMING_PROFESSIONAL_FORENAME",
    "PERFORMING_PROFESSIONAL_SURNAME",
    "RECORDED_DATE",
    "PRIMARY_SOURCE",
    "VACCINATION_PROCEDURE_CODE",
    "VACCINATION_PROCEDURE_TERM",
    "DOSE_SEQUENCE",
    "VACCINE_PRODUCT_CODE",
    "VACCINE_PRODUCT_TERM",
    "VACCINE_MANUFACTURER",
    "BATCH_NUMBER",
    "EXPIRY_DATE",
    "SITE_OF_VACCINATION_CODE",
    "SITE_OF_VACCINATION_TERM",
    "ROUTE_OF_VACCINATION_CODE",
    "ROUTE_OF_VACCINATION_TERM",
    "DOSE_AMOUNT",
    "DOSE_UNIT_CODE",
    "DOSE_UNIT_TERM",
    "INDICATION_CODE",
    "LOCATION_CODE",
    "LOCATION_CODE_TYPE_URI",
]

# Creating the required dictionaries in the specified order
all_fields = {key: (mandatory_fields.get(key) or non_mandatory_fields.get(key) or "") for key in field_order}
mandatory_fields_only = {key: (mandatory_fields.get(key) or "") for key in field_order}
critical_fields_only = {key: (critical_fields.get(key) or "") for key in field_order}

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


# -----------------------------------------------------
# FHIR IMMS RESOURCES MAPPED FROM FIELDS DICTIONARIES
all_fields_fhir_imms_resource = {
    "resourceType": "Immunization",
    "contained": [
        {
            "resourceType": "Patient",
            "id": "Patient1",
            "identifier": [{"system": Urls.NHS_NUMBER, "value": "9732928395"}],
            "name": [{"family": "PEEL", "given": ["PHYLIS"]}],
            "gender": "male",
            "birthDate": "2008-02-17",
            "address": [{"postalCode": "WD25 0DZ"}],
        },
        {"resourceType": "Practitioner", "id": "Practitioner1", "name": [{"family": "O'Reilly", "given": ["Ellena"]}]},
    ],
    "extension": [
        {
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": Urls.SNOMED,
                        "code": "956951000000104",
                        "display": "RSV vaccination in pregnancy (procedure)",
                    }
                ]
            },
        }
    ],
    "identifier": [
        {
            "system": "https://www.ravs.england.nhs.uk/",
            "value": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
        }
    ],
    "status": "completed",
    "vaccineCode": {
        "coding": [
            {
                "system": Urls.SNOMED,
                "code": "42223111000001107",
                "display": "Quadrivalent influenza vaccine (split virion, inactivated)",
            }
        ]
    },
    "patient": {"reference": "#Patient1"},
    "occurrenceDateTime": "2024-09-04T18:33:25+00:00",
    "recorded": "2024-09-04",
    "primarySource": True,
    "manufacturer": {"display": "Sanofi Pasteur"},
    "location": {"identifier": {"value": "RJC02", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}},
    "lotNumber": "BN92478105653",
    "expirationDate": "2024-09-15",
    "site": {"coding": [{"system": Urls.SNOMED, "code": "368209003", "display": "Right arm"}]},
    "route": {"coding": [{"system": Urls.SNOMED, "code": "1210999013", "display": "Intradermal use"}]},
    "doseQuantity": {
        "value": Decimal("0.3"),
        "unit": "Inhalation - unit of product usage",
        "system": Urls.SNOMED,
        "code": "2622896019",
    },
    "performer": [
        {
            "actor": {
                "type": "Organization",
                "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "RVVKC"},
            }
        },
        {"actor": {"reference": "#Practitioner1"}},
    ],
    "reasonCode": [{"coding": [{"code": "1037351000000105", "system": Urls.SNOMED}]}],
    "protocolApplied": [
        {
            "targetDisease": TARGET_DISEASE_ELEMENTS[Vaccine.RSV.value],
            "doseNumberPositiveInt": 1,
        }
    ],
}

mandatory_fields_only_fhir_imms_resource = {
    "resourceType": "Immunization",
    "contained": [
        {
            "resourceType": "Patient",
            "id": "Patient1",
            "name": [{"family": "PEEL", "given": ["PHYLIS"]}],
            "gender": "male",
            "birthDate": "2008-02-17",
            "address": [{"postalCode": "WD25 0DZ"}],
        },
    ],
    "extension": [
        {
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            "valueCodeableConcept": {
                "coding": [
                    {
                        "system": Urls.SNOMED,
                        "code": "956951000000104",
                    }
                ]
            },
        }
    ],
    "identifier": [
        {
            "system": "https://www.ravs.england.nhs.uk/",
            "value": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
        }
    ],
    "status": "completed",
    "vaccineCode": {"coding": [{"system": Urls.NULL_FLAVOUR_CODES, "code": "NAVU", "display": "Not available"}]},
    "patient": {"reference": "#Patient1"},
    "occurrenceDateTime": "2024-09-04T18:33:25+00:00",
    "recorded": "2024-09-04",
    "primarySource": True,
    "location": {"identifier": {"value": "RJC02", "system": "https://fhir.nhs.uk/Id/ods-organization-code"}},
    "performer": [
        {
            "actor": {
                "type": "Organization",
                "identifier": {"system": "https://fhir.nhs.uk/Id/ods-organization-code", "value": "RVVKC"},
            }
        },
    ],
    "protocolApplied": [
        {
            "targetDisease": TARGET_DISEASE_ELEMENTS[Vaccine.RSV.value],
            "doseNumberString": "Dose sequence not recorded",
        }
    ],
}

critical_fields_only_fhir_imms_resource = {
    "resourceType": "Immunization",
    "status": "completed",
    "vaccineCode": {"coding": [{"system": Urls.NULL_FLAVOUR_CODES, "code": "NAVU", "display": "Not available"}]},
    "identifier": [{"system": "a_unique_id_uri", "value": "a_unique_id"}],
    "protocolApplied": [
        {
            "targetDisease": TARGET_DISEASE_ELEMENTS[Vaccine.RSV.value],
            "doseNumberString": "Dose sequence not recorded",
        }
    ],
}


def create_mock_api_response(status_code: int, diagnostics: str = None) -> requests.Response:
    mock_response = MagicMock()
    if status_code != 200:
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": status_code,
                "body": '{"resourceType": "OperationOutcome", "id": "45b552ca-755a-473f-84df-c7e7767bd2ac",'
                '"issue": [{"severity": "error","code": "error",'
                '"details": {"coding": [{"system": "test", "code": "unknown-error"}]},'
                '"diagnostics": "unknown-error"}]}',
            }
        )
    if diagnostics is None and status_code == 200:
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": status_code,
                "body": '{"resourceType": "Bundle", "type": "searchset",'
                '"entry": [{"resource": {"id": "277befd9-574e-47fe-a6ee-189858af3bb0",'
                '"meta": {"versionId": 2}}}], "total": 1}',
            }
        )
    if diagnostics and status_code == 200:
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": status_code,
                "body": '{"resourceType": "Bundle", "type": "searchset",' '"entry": [], "total": 0}',
            }
        )
    return mock_response
