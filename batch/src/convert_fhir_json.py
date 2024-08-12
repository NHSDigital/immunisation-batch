import json
from datetime import datetime, timezone


def convert_to_fhir_json(row, vaccine_type):
    vaccine_type = vaccine_type.lower()

    def map_target_disease(vaccine_type):
        if vaccine_type == "covid19":
            return [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "840539006",
                            "display": "Disease caused by severe acute respiratory syndrome coronavirus 2"
                        }
                    ]
                }
            ]
        elif vaccine_type == "flu":
            return [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "6142004",
                            "display": "Influenza"
                        }
                    ]
                }
            ]
        elif vaccine_type == "mmr":
            return [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "14189004",
                            "display": "Measles"
                        }
                    ]
                },
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "36989005",
                            "display": "Mumps"
                        }
                    ]
                },
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "36653000",
                            "display": "Rubella"
                        }
                    ]
                }
            ]
        else:
            return []

    def convert_to_boolean(value):
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        else:
            return False

    def map_gender(gender_code):
        gender_map = {
            "1": "male",
            "2": "female",
            "9": "other",
            "0": "unknown"
        }
        return gender_map.get(gender_code, "unknown")

    def add_if_not_empty(dictionary, key, value):
        if value:
            dictionary[key] = value

    try:
        fhir_json = {
            "resourceType": "Immunization",
            "contained": []
        }

        # Practitioner
        practitioner = {
            "resourceType": "Practitioner",
            "id": "Pract1"
        }
        name = {}
        add_if_not_empty(name, "family", row.get('PERFORMING_PROFESSIONAL_SURNAME', ''))
        given = row.get('PERFORMING_PROFESSIONAL_FORENAME', '')
        if given:
            name["given"] = [given]
        if name:
            practitioner["name"] = [name]
        if practitioner:
            fhir_json["contained"].append(practitioner)

        # Patient
        patient = {
            "resourceType": "Patient",
            "id": "Pat1",
        }
        # Create the identifier only if 'NHS_NUMBER' has a value
        nhs_number = row.get('NHS_NUMBER', '')
        if nhs_number:
            identifier = {
                "system": "https://fhir.nhs.uk/Id/nhs-number",
                "value": nhs_number
            }
            patient["identifier"] = [identifier]
        name = {}
        add_if_not_empty(name, "family", row.get('PERSON_SURNAME', ''))
        given = row.get('PERSON_FORENAME', '')
        if given:
            name["given"] = [given]
        if name:
            patient["name"] = [name]
        add_if_not_empty(patient, "gender", map_gender(row.get('PERSON_GENDER_CODE', '0')))
        add_if_not_empty(patient, "birthDate", row.get('PERSON_DOB', ''))
        address = {}
        add_if_not_empty(address, "postalCode", row.get('PERSON_POSTCODE', ''))
        if address:
            patient["address"] = [address]
        if patient:
            fhir_json["contained"].append(patient)

        # Immunization Extension
        extension = {
            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
            "valueCodeableConcept": {
                "coding": []
            }
        }

        # Creating the coding dictionary
        coding = {
            "system": "http://snomed.info/sct"
        }
        add_if_not_empty(coding, "code", row.get('VACCINATION_PROCEDURE_CODE', ''))
        add_if_not_empty(coding, "display", row.get('VACCINATION_PROCEDURE_TERM', ''))

        # Only append coding if both 'code' and 'display' are present
        if "code" in coding and "display" in coding or "system" in coding:  # Ensure both code and display exist
            extension["valueCodeableConcept"]["coding"].append(coding)

        # Only add the extension to the fhir_json if coding was added
        if extension["valueCodeableConcept"]["coding"]:
            fhir_json["extension"] = [extension]

        # Identifier
        identifier = {}

        # Use add_if_not_empty to conditionally add 'system' and 'value'
        add_if_not_empty(identifier, "system", row.get('UNIQUE_ID_URI', ''))
        add_if_not_empty(identifier, "value", row.get('UNIQUE_ID', ''))

        # Only add the identifier to fhir_json if at least one field is present
        if identifier:
            fhir_json["identifier"] = [identifier]

        # Vaccine Code
        vaccine_code = {
            "coding": []
        }

        coding = {
            "system": "http://snomed.info/sct"
        }

        # Use add_if_not_empty to conditionally add 'code' and 'display'
        add_if_not_empty(coding, "code", row.get('VACCINE_PRODUCT_CODE', ''))
        add_if_not_empty(coding, "display", row.get('VACCINE_PRODUCT_TERM', ''))

        # Only append the coding if it has at least one of 'code', 'display', or 'system'
        if coding.get("code") or coding.get("display") or coding.get("system"):
            vaccine_code["coding"].append(coding)

        # Only add vaccineCode to fhir_json if the coding list is not empty
        if vaccine_code["coding"]:
            fhir_json["vaccineCode"] = vaccine_code

        # Patient Reference
        fhir_json["patient"] = {
            "reference": "#Pat1"
        }

        # Occurrence DateTime
        # Convert the 'DATE_AND_TIME' to a datetime object
        date_time_str = row.get('DATE_AND_TIME', '')
        if date_time_str:
            date_time_obj = datetime.strptime(date_time_str, '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
            formatted_date_time = date_time_obj.strftime("%Y-%m-%dT%H:%M:%S+00:00")

            # Add the formatted datetime to the fhir_json if it's not empty
            add_if_not_empty(fhir_json, "occurrenceDateTime", formatted_date_time)
        # Recorded Date
        recorded_str = row.get('RECORDED_DATE', '')
        if recorded_str:
            recorded_date_obj = datetime.strptime(recorded_str, '%Y%m%d').date()

            # Add the date to the fhir_json if it's not empty
            add_if_not_empty(fhir_json, "recorded", recorded_date_obj.isoformat())

        # Primary Source
        add_if_not_empty(fhir_json, "primarySource", convert_to_boolean(row.get('PRIMARY_SOURCE', 'false')))

        # Manufacturer
        manufacturer = {
            "display": row.get('VACCINE_MANUFACTURER', '')
        }
        if manufacturer["display"]:
            fhir_json["manufacturer"] = manufacturer

        # Location
        location = {
            "type": "Location"
        }

        identifier = {}
        # Use add_if_not_empty to conditionally add 'value' and 'system'
        add_if_not_empty(identifier, "value", row.get('LOCATION_CODE', ''))
        add_if_not_empty(identifier, "system", row.get('LOCATION_CODE_TYPE_URI', ''))

        # Only add the identifier to the location if it's not empty
        if identifier:
            location["identifier"] = identifier

        # Only add the location to fhir_json if it has either an identifier or a type
        if location.get("identifier") or location.get("type"):
            fhir_json["location"] = location

        # Lot Number
        add_if_not_empty(fhir_json, "lotNumber", row.get('BATCH_NUMBER', ''))

        # Expiration Date
        expiry_date_str = row.get('EXPIRY_DATE', '')
        if expiry_date_str:
            expiry_date_obj = datetime.strptime(expiry_date_str, '%Y%m%d').date()

            # Add the date to the fhir_json if it's not empty
            add_if_not_empty(fhir_json, "expirationDate", expiry_date_obj.isoformat())

        # Site
        site = {
            "coding": []
        }

        coding = {
            "system": "http://snomed.info/sct"
        }

        # Use add_if_not_empty to conditionally add 'code' and 'display'
        add_if_not_empty(coding, "code", row.get('SITE_OF_VACCINATION_CODE', ''))
        add_if_not_empty(coding, "display", row.get('SITE_OF_VACCINATION_TERM', ''))

        # Only append the coding if it has at least one of 'code' or 'display'
        if coding.get("code") or coding.get("display") or coding.get("system"):
            site["coding"].append(coding)

        # Only add site to fhir_json if the coding list is not empty
        if site["coding"]:
            fhir_json["site"] = site

        # Route
        route = {
            "coding": []
        }
        coding = {
            "system": "http://snomed.info/sct",
        }
        add_if_not_empty(coding, "code", row.get('ROUTE_OF_VACCINATION_CODE', ''))
        add_if_not_empty(coding, "display", row.get('ROUTE_OF_VACCINATION_TERM', ''))
        # Only append the coding if it has at least one of 'code' or 'display'
        if coding.get("code") or coding.get("display") or coding.get("system"):
            route["coding"].append(coding)

        # Only add route to fhir_json if the coding list is not empty
        if route["coding"]:
            fhir_json["route"] = route

        # Dose Quantity
        dose_quantity = {
            "system": "http://unitsofmeasure.org"
        }

        # Use add_if_not_empty to conditionally add 'value', 'unit', and 'code'
        add_if_not_empty(dose_quantity, "value", row.get('DOSE_AMOUNT', ''))
        add_if_not_empty(dose_quantity, "unit", row.get('DOSE_UNIT_TERM', ''))
        add_if_not_empty(dose_quantity, "code", row.get('DOSE_UNIT_CODE', ''))
        if "value" in dose_quantity:
            value_str = dose_quantity["value"]
            if '.' in value_str:
                dose_quantity["value"] = float(value_str)
            else:
                dose_quantity["value"] = int(value_str)
        # Only add doseQuantity to fhir_json if it has any relevant fields
        if "value" in dose_quantity or "unit" in dose_quantity or "code" in dose_quantity or "system" in dose_quantity:
            fhir_json["doseQuantity"] = dose_quantity

        # Performer
        performer = [
            {
                "actor": {
                    "reference": "#Pract1"
                }
            },
            {
                "actor": {
                    "type": "Organization",
                    "identifier": {}
                }
            }
        ]

        # Use add_if_not_empty to conditionally add 'system' and 'value'
        add_if_not_empty(performer[1]["actor"]["identifier"], "system", row.get('SITE_CODE_TYPE_URI', ''))
        add_if_not_empty(performer[1]["actor"]["identifier"], "value", row.get('SITE_CODE', ''))

        # Only add the 'identifier' field if it has content
        if performer[1]["actor"]["identifier"]:
            fhir_json["performer"] = performer
        else:
            # Remove the second performer entry if the identifier is empty
            fhir_json["performer"] = [performer[0]]

        # Reason Code
        reason_code = {
            "coding": [
                {
                    "code": row.get('INDICATION_CODE', ''),
                    "system": "http://snomed.info/sct"
                }
            ]
        }
        if reason_code["coding"][0]["code"] or reason_code["coding"][0]["system"]:
            fhir_json["reasonCode"] = [reason_code]

        # Protocol Applied
        protocol_applied = {
            "targetDisease": map_target_disease(vaccine_type),
            "doseNumberPositiveInt": int(row.get('DOSE_SEQUENCE', 0))
        }
        fhir_json["protocolApplied"] = [protocol_applied]
        final_json = json.dumps(fhir_json)
        return final_json, True
    except KeyError as e:
        print(f"Missing field in row data: {e}")
        return None, False
    except ValueError as e:
        print(f"Value error in row data: {e}")
        return None, False
