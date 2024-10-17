"""Constants for use when testing decorators"""

from decimal import Decimal

VALID_NHS_NUMBER = "1345678940"
ADDRESS_UNKNOWN_POSTCODE = "ZZ99 3WZ"


class ExtensionItems:
    """Class containing standard extension items"""

    vaccination_procedure_url = "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure"
    snomed_url = "http://snomed.info/sct"

    vaccination_procedure = {
        "url": vaccination_procedure_url,
        "valueCodeableConcept": {
            "coding": [
                {
                    "system": snomed_url,
                    "code": "a_vaccination_procedure_code",
                    "display": "a_vaccination_procedure_term",
                }
            ]
        },
    }


class AllHeaders:
    """Class containing all headers for each decorator"""

    immunization = {
        "indication_code": "INDICATION_CODE",
        "recorded_date": "20000101",
        "unique_id": "UNIQUE_ID_123",
        "unique_id_uri": "unique_id_uri",
    }

    patient = {
        "person_surname": "surname",
        "person_forename": "forename",
        "person_gender_code": "1",
        "person_dob": "20000101",
        "person_postcode": "ZZ99 3WZ",
        "nhs_number": "1345678940",
    }

    vaccine = {
        "vaccine_product_code": "a_vacc_code",
        "vaccine_product_term": "a_vacc_term",
        "vaccine_manufacturer": "a_manufacturer",
        "expiry_date": "20000101",
        "batch_number": "a_batch_number",
    }

    vaccination = {
        "vaccination_procedure_code": "a_vaccination_procedure_code",
        "vaccination_procedure_term": "a_vaccination_procedure_term",
        "date_and_time": "20000101T11111101",
        "primary_source": "True",
        "site_of_vaccination_code": "a_vacc_site_code",
        "site_of_vaccination_term": "a_vacc_site_term",
        "route_of_vaccination_code": "a_vacc_route_code",
        "route_of_vaccination_term": "a_vacc_route_term",
        "dose_amount": "0.5",
        "dose_unit_term": "a_dose_unit_term",
        "dose_unit_code": "a_dose_unit_code",
        "dose_sequence": "3",
    }

    performer = {
        "site_code_type_uri": "a_site_code_type_uri",
        "site_code": "a_site_code",
        "performing_professional_surname": "a_prof_surname",
        "performing_professional_forename": "a_prof_forename",
        "location_code": "a_location_code",
        "location_code_type_uri": "a_location_code_uri",
    }


class AllHeadersExpectedOutput:
    """
    Class containing the expected output for each decorator when given all headers (with values as defined in the
    AllHeaders class)
    """

    immunization = {
        "resourceType": "Immunization",
        "contained": [],
        "status": "completed",
        "reasonCode": [{"coding": [{"code": "INDICATION_CODE"}]}],
        "recorded": "2000-01-01",
        "identifier": [{"system": "unique_id_uri", "value": "UNIQUE_ID_123"}],
    }

    patient = {
        "resourceType": "Immunization",
        "status": "completed",
        "contained": [
            {
                "resourceType": "Patient",
                "id": "Patient1",
                "identifier": [
                    {
                        "system": "https://fhir.nhs.uk/Id/nhs-number",
                        "value": VALID_NHS_NUMBER,
                    }
                ],
                "name": [{"family": "surname", "given": ["forename"]}],
                "gender": "male",
                "birthDate": "2000-01-01",
                "address": [{"postalCode": ADDRESS_UNKNOWN_POSTCODE}],
            },
        ],
        "patient": {"reference": "#Patient1"},
    }

    vaccine = {
        "resourceType": "Immunization",
        "status": "completed",
        "contained": [],
        "vaccineCode": {
            "coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_code", "display": "a_vacc_term"}]
        },
        "manufacturer": {"display": "a_manufacturer"},
        "lotNumber": "a_batch_number",
        "expirationDate": "2000-01-01",
    }

    vaccination = {
        "resourceType": "Immunization",
        "status": "completed",
        "contained": [],
        "extension": [ExtensionItems.vaccination_procedure],
        "occurrenceDateTime": "2000-01-01T11:11:11+01:00",
        "primarySource": True,
        "site": {
            "coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_site_code", "display": "a_vacc_site_term"}]
        },
        "route": {
            "coding": [
                {"system": "http://snomed.info/sct", "code": "a_vacc_route_code", "display": "a_vacc_route_term"}
            ]
        },
        "doseQuantity": {
            "value": Decimal(0.5),
            "unit": "a_dose_unit_term",
            "system": "http://unitsofmeasure.org",
            "code": "a_dose_unit_code",
        },
        "protocolApplied": [{"doseNumberPositiveInt": 3}],
    }

    performer = {
        "resourceType": "Immunization",
        "status": "completed",
        "contained": [
            {
                "resourceType": "Practitioner",
                "id": "Practitioner1",
                "name": [{"family": "a_prof_surname", "given": ["a_prof_forename"]}],
            }
        ],
        "performer": [
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {"system": "a_site_code_type_uri", "value": "a_site_code"},
                }
            },
            {"actor": {"reference": "#Practitioner1"}},
        ],
        "location": {
            "type": "Location",
            "identifier": {"value": "a_location_code", "system": "a_location_code_uri"},
        },
    }
