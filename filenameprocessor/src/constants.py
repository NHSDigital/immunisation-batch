"""Constants for the filenameprocessor lambda"""


class Constants:
    """Constants for the filenameprocessor lambda"""

    VALID_VACCINE_TYPES = ["FLU", "COVID19", "MMR"]

    VALID_VERSIONS = ["V5"]

    EXPECTED_CSV_HEADERS = [
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

    ODS_TO_SUPPLIER_MAPPINGS = {
        "YGM41": "EMIS",
        "8J1100001": "PINNACLE",
        "8HK48": "SONAR",
        "YGA": "TPP",
        "0DE": "AGEM-NIVS",
        "0DF": "NIMS",
        "8HA94": "EVA",
        "X26": "RAVS",
        "YGMYH": "MEDICAL_DIRECTOR",
        "W00": "WELSH_DA_1",
        "W000": "WELSH_DA_2",
        "ZT001": "NORTHERN_IRELAND_DA",
        "YA7": "SCOTLAND_DA",
        "N2N9I": "COVID19_VACCINE_RESOLUTION_SERVICEDESK",
        "YGJ": "EMIS",
        "DPSREDUCED": "DPSREDUCED",
        "DPSFULL": "DPSFULL",
    }

    # Mapping of long supplier names to shorter ones to meet 80 character SQS queue limit
    SUPPLIER_TO_SQSQUEUE_MAPPINGS = {
        "EMIS": "EMIS",
        "PINNACLE": "PINN",
        "SONAR": "SONAR",
        "TPP": "TPP",
        "AGEM-NIVS": "AGEM_NIVS",
        "NIMS": "NIMS",
        "EVA": "EVA",
        "RAVS": "RAVS",
        "MEDICAL_DIRECTOR": "M_D",
        "WELSH_DA_1": "WELSHDA1",
        "WELSH_DA_2": "WELSHDA2",
        "NORTHERN_IRELAND_DA": "NIREDA",
        "SCOTLAND_DA": "SCOTDA",
        "COVID19_VACCINE_RESOLUTION_SERVICEDESK": "C19VAX_SRVCEDSK",
        "DPSREDUCED": "DPS",
        "DPSFULL": "DPS",
    }


