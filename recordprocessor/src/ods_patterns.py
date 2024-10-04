"""Dictionary mapping supplier ODS CODEs to the supplier name, this is used for identifying
supplier queue"""

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
    "DPSREDUCED": "DPS",
    "DPSFULL": "DPS",
}
