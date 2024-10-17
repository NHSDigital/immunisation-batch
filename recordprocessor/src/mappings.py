"""Mappings for converting vaccine type into target disease FHIR element"""

from dataclasses import dataclass


@dataclass
class DiseaseCodes:
    """Disease Codes"""

    covid_19: str = "840539006"
    flu: str = "6142004"
    measles: str = "14189004"
    mumps: str = "36989005"
    rubella: str = "36653000"
    rsv: str = "55735004"


class DiseaseDisplayTerms:
    """Disease display terms which correspond to disease codes"""

    covid_19: str = "Disease caused by severe acute respiratory syndrome coronavirus 2"
    flu: str = "Influenza"
    measles: str = "Measles"
    mumps: str = "Mumps"
    rubella: str = "Rubella"
    rsv: str = "Respiratory syncytial virus infection (disorder)"


VACCINE_DISEASE_MAPPING = {
    "covid19": ["covid_19"],
    "flu": ["flu"],
    "mmr": ["measles", "mumps", "rubella"],
    "rsv": ["rsv"],
}


def map_target_disease(vaccine_type: str) -> list:
    """Returns the target disease element for the given vaccine type using the vaccine_disease_mapping"""
    # Retrieve the disease types associated with the vaccine
    diseases = VACCINE_DISEASE_MAPPING.get(vaccine_type, [])

    # Dynamically form the disease coding information based on the retrieved diseases
    return [
        {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": getattr(DiseaseCodes, disease),
                    "display": getattr(DiseaseDisplayTerms, disease),
                }
            ]
        }
        for disease in diseases
    ]
