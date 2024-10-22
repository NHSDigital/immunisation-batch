"""Mappings for converting vaccine type into target disease FHIR element"""

from constants import Urls


class DiseaseCodes:
    """Disease Codes"""

    COVID_19: str = "840539006"
    FLU: str = "6142004"
    MEASLES: str = "14189004"
    MUMPS: str = "36989005"
    RUBELLA: str = "36653000"
    RSV: str = "55735004"


class DiseaseDisplayTerms:
    """Disease display terms which correspond to disease codes"""

    COVID_19: str = "Disease caused by severe acute respiratory syndrome coronavirus 2"
    FLU: str = "Influenza"
    MEASLES: str = "Measles"
    MUMPS: str = "Mumps"
    RUBELLA: str = "Rubella"
    RSV: str = "Respiratory syncytial virus infection (disorder)"


VACCINE_DISEASE_MAPPING = {
    "COVID19": ["COVID_19"],
    "FLU": ["FLU"],
    "MMR": ["MEASLES", "MUMPS", "RUBELLA"],
    "RSV": ["RSV"],
}


def map_target_disease(vaccine_type: str) -> list:
    """Returns the target disease element for the given vaccine type using the vaccine_disease_mapping"""
    diseases = VACCINE_DISEASE_MAPPING.get(vaccine_type.upper(), [])
    return [
        {
            "coding": [
                {
                    "system": Urls.SNOMED,
                    "code": getattr(DiseaseCodes, disease),
                    "display": getattr(DiseaseDisplayTerms, disease),
                }
            ]
        }
        for disease in diseases
    ]
