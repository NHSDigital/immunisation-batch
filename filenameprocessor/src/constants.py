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

    # Mappings from ODS code to supplier name.
    # NOTE: Any ODS code not found in this dictionary's keys is invalid for this service
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
