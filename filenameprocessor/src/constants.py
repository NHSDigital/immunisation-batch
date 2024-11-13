"""Constants for the filenameprocessor lambda"""


class Constants:
    """Constants for the filenameprocessor lambda"""

    VALID_VACCINE_TYPES = ["FLU", "COVID19", "MMR", "RSV"]

    VALID_VERSIONS = ["V5"]

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
