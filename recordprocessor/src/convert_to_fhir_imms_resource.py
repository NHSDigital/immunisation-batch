""""Decorators to add the relevant fields to the FHIR immunization resource from the batch stream"""

from typing import List, Callable, Dict
from csv import DictReader

from utils_for_fhir_conversion import _is_not_empty, Create, Add, Convert
from mappings import map_target_disease


ImmunizationDecorator = Callable[[Dict, Dict[str, str]], None]
"""
A decorator function (Callable) takes current immunization object and adds appropriate fields to it. 
NOTE: The decorators are order independent. They can be called in any order, so don't rely on previous changes.
NOTE: decorate function is the only public function. If you add a new decorator, call it in this function.
NOTE: NO VALIDATION should be performed. Validation is left to the Imms API
NOTE: An overarching data rule is that where data is not present the field should not be added to the FHIR Immunization
resource. Therefore before adding an element it is necessary to check that at least one of its values is non-empty.
"""


def _decorate_immunization(imms: dict, record: DictReader):
    """Every thing related to the immunization object itself like status and identifier"""
    Add.custom_item(
        imms,
        "reasonCode",
        [indication_code := record.get("indication_code")],
        [{"coding": [Create.dictionary({"code": indication_code})]}],
    )

    Add.item(imms, "recorded", record.get("recorded_date"), Convert.date)

    Add.list_of_dict(imms, "identifier", {"value": record.get("unique_id"), "system": record.get("unique_id_uri")})


def _decorate_patient(imms: dict, record: Dict[str, str]):
    """Create the 'patient' object and append to 'contained' list"""
    patient_values = [
        person_surname := record.get("person_surname"),
        person_forename := record.get("person_forename"),
        person_gender_code := record.get("person_gender_code"),
        person_dob := record.get("person_dob"),
        person_postcode := record.get("person_postcode"),
        nhs_number := record.get("nhs_number"),
    ]

    # Add patient if there is at least one non-empty patient value
    if any(_is_not_empty(value) for value in patient_values):

        # Set up patient
        internal_patient_id = "Patient1"
        imms["patient"] = {"reference": f"#{internal_patient_id}"}
        patient = {"id": internal_patient_id, "resourceType": "Patient"}

        Add.item(patient, "birthDate", person_dob, Convert.date)

        Add.item(patient, "gender", person_gender_code, Convert.gender_code)

        Add.list_of_dict(patient, "address", {"postalCode": person_postcode})

        Add.custom_item(
            patient, "identifier", nhs_number, [{"system": "https://fhir.nhs.uk/Id/nhs-number", "value": nhs_number}]
        )

        # Add patient name if there is at least one non-empty patient name value
        if any(_is_not_empty(value) for value in [person_surname, person_forename]):
            patient["name"] = [{}]
            Add.item(patient["name"][0], "family", person_surname)
            Add.custom_item(patient["name"][0], "given", [person_forename], [person_forename])

        imms["contained"].append(patient)


def _decorate_vaccine(imms: dict, record: Dict[str, str]):
    """Vaccine refers to the physical vaccine product the manufacturer"""
    Add.snomed(imms, "vaccineCode", record.get("vaccine_product_code"), record.get("vaccine_product_term"))

    Add.dictionary(imms, "manufacturer", {"display": record.get("vaccine_manufacturer")})

    Add.item(imms, "expirationDate", record.get("expiry_date"), Convert.date)

    Add.item(imms, "lotNumber", record.get("batch_number"))


def _decorate_vaccination(imms: dict, record: Dict[str, str]):
    """Vaccination refers to the actual administration of a vaccine to a patient"""
    vaccination_extension_values = [
        vaccination_procedure_code := record.get("vaccination_procedure_code"),
        vaccination_procedure_term := record.get("vaccination_procedure_term"),
    ]

    # Add extension item if at least one extension item value is non-empty
    if any(_is_not_empty(value) for value in vaccination_extension_values):
        imms["extension"] = []

        imms["extension"].append(
            Create.extension_item(
                url="https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                system="http://snomed.info/sct",
                code=vaccination_procedure_code,
                display=vaccination_procedure_term,
            )
        )

    Add.item(imms, "occurrenceDateTime", record.get("date_and_time"), Convert.date_time)

    Add.item(imms, "primarySource", record.get("primary_source"), Convert.boolean)

    Add.snomed(imms, "site", record.get("site_of_vaccination_code"), record.get("site_of_vaccination_term"))

    Add.snomed(imms, "route", record.get("route_of_vaccination_code"), record.get("route_of_vaccination_term"))

    dose_quantity_values = [
        dose_amount := record.get("dose_amount"),
        dose_unit_term := record.get("dose_unit_term"),
        dose_unit_code := record.get("dose_unit_code"),
    ]
    dose_quantity_dict = {
        "value": Convert.integer_or_decimal(dose_amount),
        "unit": dose_unit_term,
        "system": "http://unitsofmeasure.org",
        "code": dose_unit_code,
    }
    Add.custom_item(imms, "doseQuantity", dose_quantity_values, Create.dictionary(dose_quantity_dict))


def _decorate_performer(imms: dict, record: Dict[str, str]):
    """Create the 'practitioner' object and 'organization' and append them to the 'contained' list"""
    organization_values = [
        site_code_type_uri := record.get("site_code_type_uri"),
        site_code := record.get("site_code"),
    ]
    practitioner_values = [
        performing_prof_surname := record.get("performing_professional_surname"),
        performing_prof_forename := record.get("performing_professional_forename"),
    ]
    peformer_values = organization_values + practitioner_values

    # Add performer if there is at least one non-empty performer value
    if any(_is_not_empty(value) for value in peformer_values):
        imms["performer"] = []

        # Add organization if there is at least one non-empty organization value
        if any(_is_not_empty(value) for value in organization_values):
            organization = {"actor": {"type": "Organization"}}

            Add.dictionary(organization["actor"], "identifier", {"system": site_code_type_uri, "value": site_code})

            imms["performer"].append(organization)

        # Add practitioner if there is at least one practitioner value
        if any(_is_not_empty(value) for value in practitioner_values):

            # Set up the practitioner
            internal_practitioner_id = "Practitioner1"
            practitioner = {"resourceType": "Practitioner", "id": internal_practitioner_id}
            imms["performer"].append({"actor": {"reference": f"#{internal_practitioner_id}"}})

            # Add practitioner name if there is at least one non-empty practitioner name value
            if any(_is_not_empty(value) for value in [performing_prof_surname, performing_prof_forename]):
                practitioner["name"] = [{}]
                Add.item(practitioner["name"][0], "family", performing_prof_surname)
                Add.custom_item(
                    practitioner["name"][0], "given", [performing_prof_forename], [performing_prof_forename]
                )

            imms["contained"].append(practitioner)

    Add.custom_item(
        imms,
        "location",
        [location_code := record.get("location_code"), location_code_type_uri := record.get("location_code_type_uri")],
        {
            "type": "Location",
            "identifier": Create.dictionary({"value": location_code, "system": location_code_type_uri}),
        },
    )


def _decorate_protocol_applied(imms: dict, record: Dict[str, str], vaccine_type):
    protocol_applied = [{"targetDisease": map_target_disease(vaccine_type)}]
    Add.item(protocol_applied, "doseNumberPositiveInt", record.get("dose_sequence"), Convert.integer)
    imms["protocolApplied"] = protocol_applied


all_decorators: List[ImmunizationDecorator] = [
    _decorate_immunization,
    _decorate_patient,
    _decorate_vaccine,
    _decorate_vaccination,
    _decorate_performer,
]


def convert_to_fhir_imms_resource(row, vaccine_type):
    imms_resource = {"resourceType": "Immunization", "contained": [], "status": "completed"}
    for decorator in all_decorators:
        decorator(imms_resource, row)
    _decorate_protocol_applied(imms_resource, row, vaccine_type)
