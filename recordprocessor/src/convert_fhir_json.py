from mappings import map_target_disease
from datetime import datetime, timezone
import logging

logger = logging.getLogger()


def convert_to_fhir_json(row, vaccine_type):
    vaccine_type = vaccine_type.lower()

    def convert_to_boolean(value):
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
        else:
            return False

    def map_gender(gender_code):
        gender_map = {"1": "male", "2": "female", "9": "other", "0": "unknown"}
        return gender_map.get(gender_code, "unknown")

    def add_if_not_empty(dictionary, key, value):
        if value:
            dictionary[key] = value

    try:
        fhir_json = {"resourceType": "Immunization", "contained": []}

        # Practitioner
        name = {}
        family_name = row.get("PERFORMING_PROFESSIONAL_SURNAME", "")
        given_name = row.get("PERFORMING_PROFESSIONAL_FORENAME", "")

        # Add family name if not empty
        if family_name:
            name["family"] = family_name

        # Add given name if not empty
        if given_name:
            name["given"] = [given_name]

        # Only proceed to create and append the practitioner if any of the family and given names are present
        if name.get("family") or name.get("given"):
            practitioner = {"resourceType": "Practitioner", "id": "Pract1", "name": [name]}
            fhir_json["contained"].append(practitioner)

        # Patient
        patient = {
            "resourceType": "Patient",
            "id": "Pat1",
        }
        # Create the identifier only if 'NHS_NUMBER' has a value
        nhs_number = row.get("NHS_NUMBER", "")
        if nhs_number:
            identifier = {"system": "https://fhir.nhs.uk/Id/nhs-number", "value": nhs_number}
            patient["identifier"] = [identifier]
        name = {}
        add_if_not_empty(name, "family", row.get("PERSON_SURNAME", ""))
        given = row.get("PERSON_FORENAME", "")
        if given:
            name["given"] = [given]
        if name:
            patient["name"] = [name]
        add_if_not_empty(patient, "gender", map_gender(row.get("PERSON_GENDER_CODE", "0")))
        birthdate_str = row.get("PERSON_DOB", "")
        if birthdate_str:
            birthdate_obj = datetime.strptime(birthdate_str, "%Y%m%d").date()

            # Add the date to the fhir_json if it's not empty
            add_if_not_empty(patient, "birthDate", birthdate_obj.isoformat())
        address = {}
        add_if_not_empty(address, "postalCode", row.get("PERSON_POSTCODE", ""))
        if address:
            patient["address"] = [address]
        if patient:
            fhir_json["contained"].append(patient)

        # Immunization Extension
        extension = {
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            "valueCodeableConcept": {"coding": []},
        }

        # Creating the coding dictionary
        coding = {"system": "http://snomed.info/sct"}
        add_if_not_empty(coding, "code", row.get("VACCINATION_PROCEDURE_CODE", ""))
        add_if_not_empty(coding, "display", row.get("VACCINATION_PROCEDURE_TERM", ""))

        # Only append coding if both 'code' and 'display' are present
        if "code" in coding and "display" in coding or "system" in coding:  # Ensure both code and display exist
            extension["valueCodeableConcept"]["coding"].append(coding)

        # Only add the extension to the fhir_json if coding was added
        if extension["valueCodeableConcept"]["coding"]:
            fhir_json["extension"] = [extension]

        # Identifier
        identifier = {}

        # Use add_if_not_empty to conditionally add 'system' and 'value'
        add_if_not_empty(identifier, "system", row.get("UNIQUE_ID_URI", ""))
        add_if_not_empty(identifier, "value", row.get("UNIQUE_ID", ""))

        # Only add the identifier to fhir_json if at least one field is present
        if identifier:
            fhir_json["identifier"] = [identifier]

        # status
        fhir_json["status"] = "completed"

        # Vaccine Code
        vaccine_code = {"coding": []}

        coding = {"system": "http://snomed.info/sct"}
        vaccine_product_code = row.get("VACCINE_PRODUCT_CODE", "")
        if vaccine_product_code == "":
            vaccine_product_code = "NAVU"
        vaccine_product_term = row.get("VACCINE_PRODUCT_TERM", "")
        if vaccine_product_term == "":
            vaccine_product_term = "Not available"
        # Use add_if_not_empty to conditionally add 'code' and 'display'
        add_if_not_empty(coding, "code", vaccine_product_code)
        add_if_not_empty(coding, "display", vaccine_product_term)

        # Only append the coding if it has at least one of 'code', 'display', or 'system'
        if coding.get("code") or coding.get("display"):
            vaccine_code["coding"].append(coding)

        # Only add vaccineCode to fhir_json if the coding list is not empty
        if vaccine_code["coding"]:
            fhir_json["vaccineCode"] = vaccine_code

        # Patient Reference
        fhir_json["patient"] = {"reference": "#Pat1"}

        # Occurrence DateTime
        # Convert the 'DATE_AND_TIME' to a datetime object
        date_time_str = row.get("DATE_AND_TIME", "")
        if date_time_str:
            if len(date_time_str) == 8:  # Format: YYYYMMDD
                date_time_obj = datetime.strptime(date_time_str, "%Y%m%d").date()
                formatted_date_time = date_time_obj.strftime("%Y-%m-%d")
            elif len(date_time_str) == 15:  # Format: YYYYMMDDTHHMMSS
                date_time_obj = datetime.strptime(date_time_str, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                formatted_date_time = date_time_obj.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            else:
                raise ValueError(f"Unexpected DATE_AND_TIME format: {date_time_str}")

            # Add the formatted datetime to the fhir_json if it's not empty
            add_if_not_empty(fhir_json, "occurrenceDateTime", formatted_date_time)
        # Recorded Date
        recorded_str = row.get("RECORDED_DATE", "")
        if recorded_str:
            if len(recorded_str) == 8:  # Format: YYYYMMDD
                recorded_date_obj = datetime.strptime(recorded_str, "%Y%m%d").date()
                formatted_recorded_date = recorded_date_obj.strftime("%Y-%m-%d")
            elif len(recorded_str) == 15:  # Format: YYYYMMDDTHHMMSS
                recorded_date_obj = datetime.strptime(recorded_str, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
                formatted_recorded_date = recorded_date_obj.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            else:
                raise ValueError(f"Unexpected RECORDED_DATE format: {recorded_str}")

            # Add the formatted date to the fhir_json if it's not empty
            add_if_not_empty(fhir_json, "recorded", formatted_recorded_date)

        # Primary Source
        add_if_not_empty(fhir_json, "primarySource", convert_to_boolean(row.get("PRIMARY_SOURCE", "false")))

        # Manufacturer
        manufacturer = {"display": row.get("VACCINE_MANUFACTURER", "")}
        if manufacturer["display"]:
            fhir_json["manufacturer"] = manufacturer

        # Location
        location = {"type": "Location"}

        identifier = {}
        # Use add_if_not_empty to conditionally add 'value' and 'system'
        add_if_not_empty(identifier, "value", row.get("LOCATION_CODE", ""))
        add_if_not_empty(identifier, "system", row.get("LOCATION_CODE_TYPE_URI", ""))

        # Only add the identifier to the location if it's not empty
        if identifier:
            location["identifier"] = identifier

        # Only add the location to fhir_json if it has either an identifier or a type
        if location.get("identifier") or location.get("type"):
            fhir_json["location"] = location

        # Lot Number
        add_if_not_empty(fhir_json, "lotNumber", row.get("BATCH_NUMBER", ""))

        # Expiration Date
        expiry_date_str = row.get("EXPIRY_DATE", "")
        if expiry_date_str:
            expiry_date_obj = datetime.strptime(expiry_date_str, "%Y%m%d").date()

            # Add the date to the fhir_json if it's not empty
            add_if_not_empty(fhir_json, "expirationDate", expiry_date_obj.isoformat())

        # Site
        site = {"coding": []}

        coding = {"system": "http://snomed.info/sct"}

        # Use add_if_not_empty to conditionally add 'code' and 'display'
        add_if_not_empty(coding, "code", row.get("SITE_OF_VACCINATION_CODE", ""))
        add_if_not_empty(coding, "display", row.get("SITE_OF_VACCINATION_TERM", ""))

        # Only append the coding if it has at least one of 'code' or 'display'
        if coding.get("code") or coding.get("display"):
            site["coding"].append(coding)

        # Only add site to fhir_json if the coding list is not empty
        if site["coding"]:
            fhir_json["site"] = site

        # Route
        route = {"coding": []}
        coding = {
            "system": "http://snomed.info/sct",
        }
        add_if_not_empty(coding, "code", row.get("ROUTE_OF_VACCINATION_CODE", ""))
        add_if_not_empty(coding, "display", row.get("ROUTE_OF_VACCINATION_TERM", ""))
        # Only append the coding if it has at least one of 'code' or 'display'
        if coding.get("code") or coding.get("display"):
            route["coding"].append(coding)

        # Only add route to fhir_json if the coding list is not empty
        if route["coding"]:
            fhir_json["route"] = route

        # Dose Quantity
        dose_quantity = {}

        # Use add_if_not_empty to conditionally add 'value', 'unit', and 'code'
        add_if_not_empty(dose_quantity, "value", row.get("DOSE_AMOUNT", ""))
        add_if_not_empty(dose_quantity, "unit", row.get("DOSE_UNIT_TERM", ""))
        add_if_not_empty(dose_quantity, "code", row.get("DOSE_UNIT_CODE", ""))

        # Only add 'system' if DOSE_UNIT_CODE is not null or an empty string
        dose_unit_code = row.get("DOSE_UNIT_CODE", "")
        if dose_unit_code:
            dose_quantity["system"] = "http://snomed.info/sct"

        # Convert 'value' to float or int depending on its format
        if "value" in dose_quantity:
            value_str = dose_quantity["value"]
            if "." in value_str:
                dose_quantity["value"] = float(value_str)
            else:
                dose_quantity["value"] = int(value_str)
        # Only add doseQuantity to fhir_json if it has any relevant fields
        if "value" in dose_quantity or "unit" in dose_quantity or "code" in dose_quantity:
            fhir_json["doseQuantity"] = dose_quantity

        # Performer
        performer = []

        # Check if a practitioner with resourceType "Practitioner" and a valid id is present in fhir_json["contained"]
        practitioner_exists = any(
            item.get("resourceType") == "Practitioner" and item.get("id") for item in fhir_json.get("contained", [])
        )

        # Add performer with practitioner reference if practitioner exists
        if practitioner_exists:
            performer.append({"actor": {"reference": "#Pract1"}})

        # Add the second performer (Organization) with conditional identifier content
        organization_actor = {"actor": {"type": "Organization", "identifier": {}}}

        # Use add_if_not_empty to conditionally add 'system' and 'value'
        add_if_not_empty(organization_actor["actor"]["identifier"], "system", row.get("SITE_CODE_TYPE_URI", ""))
        add_if_not_empty(organization_actor["actor"]["identifier"], "value", row.get("SITE_CODE", ""))

        # Only add the organization actor if the identifier has content
        if organization_actor["actor"]["identifier"]:
            performer.append(organization_actor)

        # Add the performer array to fhir_json if it has any entries
        if performer:
            fhir_json["performer"] = performer

        # Reason Code
        # Initialize reason_code as a list
        reason_code = []

        # Prepare the coding dictionary
        coding = {
            "system": "http://snomed.info/sct",
        }

        # Add the 'code' key to the coding dictionary if 'INDICATION_CODE' is not empty
        add_if_not_empty(coding, "code", row.get("INDICATION_CODE", ""))

        # If the coding dictionary has either 'code' or 'system', append it to reason_code
        if coding.get("code"):
            reason_code.append({"coding": [coding]})

        # If reason_code is not empty, add it to fhir_json
        if reason_code:
            fhir_json["reasonCode"] = reason_code

        # Protocol Applied
        protocol_applied = {"targetDisease": map_target_disease(vaccine_type)}

        # Retrieve and process 'DOSE_SEQUENCE'
        dose_sequence = row.get("DOSE_SEQUENCE", "").strip()

        if dose_sequence.isdigit():  # Check if 'DOSE_SEQUENCE' is an integer (all digits)
            protocol_applied["doseNumberPositiveInt"] = int(dose_sequence)
        elif dose_sequence:  # If it's a non-empty string but not an integer
            protocol_applied["doseNumberString"] = dose_sequence
        else:  # If it's empty or null
            protocol_applied["doseNumberString"] = "Not recorded"

        # Add the protocolApplied to the fhir_json
        fhir_json["protocolApplied"] = [protocol_applied]

        return fhir_json, True
    except KeyError as error:
        logger.error("Missing field in row data: %s", error)
        return None, False
    except ValueError as error:
        logger.error("Value error in row data: %s", error)
        return None, False
