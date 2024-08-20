"""Dictionary mapping supplier ODS CODEs to the supplier name, this is used for identifying
supplier queue"""

ODS_PATTERNS = {
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
    "DPS_REDUCED": "DPS",
    "DPS_FULL": "DPS",
}


# Mapping of long supplier names to shorter ones to meet 80 character SQS queue limit
SUPPLIER_SQSQUEUE_MAPPINGS = {
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
    "DPS": "DPS",
}
