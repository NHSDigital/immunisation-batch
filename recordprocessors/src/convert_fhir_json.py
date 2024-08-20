from datetime import datetime, timezone
import logging
logger = logging.getLogger()


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
        birthdate_str = row.get('PERSON_DOB', '')
        if birthdate_str:
            birthdate_obj = datetime.strptime(birthdate_str, '%Y%m%d').date()

            # Add the date to the fhir_json if it's not empty
            add_if_not_empty(patient, "birthDate", birthdate_obj.isoformat())
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

        # status
        fhir_json["status"] = "completed"

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
            if len(date_time_str) == 8:  # Format: YYYYMMDD
                date_time_obj = datetime.strptime(date_time_str, '%Y%m%d').date()
                formatted_date_time = date_time_obj.strftime("%Y-%m-%d")
            elif len(date_time_str) == 15:  # Format: YYYYMMDDTHHMMSS
                date_time_obj = datetime.strptime(date_time_str, '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
                formatted_date_time = date_time_obj.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            else:
                raise ValueError(f"Unexpected DATE_AND_TIME format: {date_time_str}")

            # Add the formatted datetime to the fhir_json if it's not empty
            add_if_not_empty(fhir_json, "occurrenceDateTime", formatted_date_time)
        # Recorded Date
        recorded_str = row.get('RECORDED_DATE', '')
        if recorded_str:
            if len(recorded_str) == 8:  # Format: YYYYMMDD
                recorded_date_obj = datetime.strptime(recorded_str, '%Y%m%d').date()
                formatted_recorded_date = recorded_date_obj.strftime("%Y-%m-%d")
            elif len(recorded_str) == 15:  # Format: YYYYMMDDTHHMMSS
                recorded_date_obj = datetime.strptime(recorded_str, '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
                formatted_recorded_date = recorded_date_obj.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            else:
                raise ValueError(f"Unexpected RECORDED_DATE format: {recorded_str}")

            # Add the formatted date to the fhir_json if it's not empty
            add_if_not_empty(fhir_json, "recorded", formatted_recorded_date)

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
            "system": "http://snomed.info/sct"
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
        if "value" in dose_quantity or "unit" in dose_quantity or "code" in dose_quantity:
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
        # Initialize reason_code as a list
        reason_code = []

        # Prepare the coding dictionary
        coding = {
            "system": "http://snomed.info/sct",
        }

        # Add the 'code' key to the coding dictionary if 'INDICATION_CODE' is not empty
        add_if_not_empty(coding, "code", row.get('INDICATION_CODE', ''))

        # If the coding dictionary has either 'code' or 'system', append it to reason_code
        if coding.get("code") or coding.get("system"):
            reason_code.append({"coding": [coding]})

        # If reason_code is not empty, add it to fhir_json
        if reason_code:
            fhir_json["reasonCode"] = reason_code

        # Protocol Applied
        protocol_applied = {
            "targetDisease": map_target_disease(vaccine_type)
        }

        # Add 'doseNumberPositiveInt' if 'DOSE_SEQUENCE' is not empty
        dose_sequence = row.get('DOSE_SEQUENCE', '').strip()
        if dose_sequence:
            protocol_applied["doseNumberPositiveInt"] = int(dose_sequence)

        # Add the protocolApplied to the fhir_json
        fhir_json["protocolApplied"] = [protocol_applied]

        return fhir_json, True
    except KeyError as e:
        logger.error(f"Missing field in row data: {e}")
        return None, False
    except ValueError as e:
        logger.error(f"Value error in row data: {e}")
        return None, False


def dict_formation(row_values):

    val = {
                'NHS_NUMBER': row_values[0],
                'PERSON_FORENAME': row_values[1],
                'PERSON_SURNAME': row_values[2],
                'PERSON_DOB': row_values[3],
                'PERSON_GENDER_CODE': row_values[4],
                'PERSON_POSTCODE': row_values[5],
                'DATE_AND_TIME': row_values[6],
                'SITE_CODE': row_values[7],
                'SITE_CODE_TYPE_URI': row_values[8],
                'UNIQUE_ID': row_values[9],
                'UNIQUE_ID_URI': row_values[10],
                'ACTION_FLAG': row_values[11],
                'PERFORMING_PROFESSIONAL_FORENAME': row_values[12],
                'PERFORMING_PROFESSIONAL_SURNAME': row_values[13],
                'RECORDED_DATE': row_values[14],
                'PRIMARY_SOURCE': row_values[15],
                'VACCINATION_PROCEDURE_CODE': row_values[16],
                'VACCINATION_PROCEDURE_TERM': row_values[17],
                'DOSE_SEQUENCE': row_values[18],
                'VACCINE_PRODUCT_CODE': row_values[19],
                'VACCINE_PRODUCT_TERM': row_values[20],
                'VACCINE_MANUFACTURER': row_values[21],
                'BATCH_NUMBER': row_values[22],
                'EXPIRY_DATE': row_values[23],
                'SITE_OF_VACCINATION_CODE': row_values[24],
                'SITE_OF_VACCINATION_TERM': row_values[25],
                'ROUTE_OF_VACCINATION_CODE': row_values[26],
                'ROUTE_OF_VACCINATION_TERM': row_values[27],
                'DOSE_AMOUNT': row_values[28],
                'DOSE_UNIT_CODE': row_values[29],
                'DOSE_UNIT_TERM': row_values[30],
                'INDICATION_CODE': row_values[31],
                'LOCATION_CODE': row_values[32],
                'LOCATION_CODE_TYPE_URI': row_values[33] if len(row_values) > 33 else ''
            }

    return val
