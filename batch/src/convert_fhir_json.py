def convert_to_fhir_json(row, vaccine_type):
    row = {
        'NHS_NUMBER': '9674963871',
        'PERSON_FORENAME': 'SABINA',
        'PERSON_SURNAME': 'GREIR',
        'PERSON_DOB': '20190131',
        'PERSON_GENDER_CODE': '2',
        'PERSON_POSTCODE': '',
        'DATE_AND_TIME': '20240610T183325',
        'SITE_CODE': 'J82067',
        'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
        'UNIQUE_ID': '0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1',
        'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
        'ACTION_FLAG': 'new',
        'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
        'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
        'RECORDED_DATE': '20240609',  #
        'PRIMARY_SOURCE': 'TRUE',
        'VACCINATION_PROCEDURE_CODE': '1303503001',
        'VACCINATION_PROCEDURE_TERM': 'Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)',
        'DOSE_SEQUENCE': '1',
        'VACCINE_PRODUCT_CODE': '42605811000001109',
        'VACCINE_PRODUCT_TERM': 'Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)',
        'VACCINE_MANUFACTURER': 'Pfizer',
        'BATCH_NUMBER': 'RSVTEST',
        'EXPIRY_DATE': '20241231',
        'SITE_OF_VACCINATION_CODE': '',
        'SITE_OF_VACCINATION_TERM': 'Left upper arm structure (body structure)',
        'ROUTE_OF_VACCINATION_CODE': '78421000',
        'ROUTE_OF_VACCINATION_TERM': 'Intramuscular route (qualifier value)',
        'DOSE_AMOUNT': '0.5',
        'DOSE_UNIT_CODE': '258773002',
        'DOSE_UNIT_TERM': 'Milliliter (qualifier value)',
        'INDICATION_CODE': '',
        'INDICATION_TERM': '',  # Not provided
        'LOCATION_CODE': 'J82067',
        'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
    }
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
            "identifier": []
        }
        identifier = {
            "system": "https://fhir.nhs.uk/Id/nhs-number",
            "value": row.get('NHS_NUMBER', '')
        }
        if identifier["value"]:
            patient["identifier"].append(identifier)
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
        coding = {
            "system": "http://snomed.info/sct",
            "code": row.get('VACCINATION_PROCEDURE_CODE', ''),
            "display": row.get('VACCINATION_PROCEDURE_TERM', '')
        }
        if coding["code"] or coding["display"]:
            extension["valueCodeableConcept"]["coding"].append(coding)
        if extension["valueCodeableConcept"]["coding"]:
            fhir_json["extension"] = [extension]

        # Identifier
        identifier = {
            "system": row.get('UNIQUE_ID_URI', ''),
            "value": row.get('UNIQUE_ID', '')
        }
        if identifier["system"] or identifier["value"]:
            fhir_json["identifier"] = [identifier]

        # Vaccine Code
        vaccine_code = {
            "coding": []
        }
        coding = {
            "system": "http://snomed.info/sct",
            "code": row.get('VACCINE_PRODUCT_CODE', ''),
            "display": row.get('VACCINE_PRODUCT_TERM', '')
        }
        if coding["code"] or coding["display"]:
            vaccine_code["coding"].append(coding)
        if vaccine_code["coding"]:
            fhir_json["vaccineCode"] = vaccine_code

        # Patient Reference
        fhir_json["patient"] = {
            "reference": "#Pat1"
        }

        # Occurrence DateTime
        add_if_not_empty(fhir_json, "occurrenceDateTime", row.get('DATE_AND_TIME', ''))

        # Recorded Date
        add_if_not_empty(fhir_json, "recorded", row.get('RECORDED_DATE', ''))

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
            "type": "Location",
            "identifier": {
                "value": row.get('LOCATION_CODE', ''),
                "system": row.get('LOCATION_CODE_TYPE_URI', '')
            }
        }
        if location["identifier"]["value"] or location["identifier"]["system"]:
            fhir_json["location"] = location

        # Lot Number
        add_if_not_empty(fhir_json, "lotNumber", row.get('BATCH_NUMBER', ''))

        # Expiration Date
        add_if_not_empty(fhir_json, "expirationDate", row.get('EXPIRY_DATE', ''))

        # Site
        site = {
            "coding": []
        }
        coding = {
            "system": "http://snomed.info/sct",
            "code": row.get('SITE_OF_VACCINATION_CODE', ''),
            "display": row.get('SITE_OF_VACCINATION_TERM', '')
        }
        if coding["code"] or coding["display"]:
            site["coding"].append(coding)
        if site["coding"]:
            fhir_json["site"] = site

        # Route
        route = {
            "coding": []
        }
        coding = {
            "system": "http://snomed.info/sct",
            "code": row.get('ROUTE_OF_VACCINATION_CODE', ''),
            "display": row.get('ROUTE_OF_VACCINATION_TERM', '')
        }
        if coding["code"] or coding["display"]:
            route["coding"].append(coding)
        if route["coding"]:
            fhir_json["route"] = route

        # Dose Quantity
        dose_quantity = {
            "value": float(row.get('DOSE_AMOUNT', 0)),
            "unit": row.get('DOSE_UNIT_TERM', ''),
            "system": "http://unitsofmeasure.org",
            "code": row.get('DOSE_UNIT_CODE', '')
        }
        if dose_quantity["value"] and (dose_quantity["unit"] or dose_quantity["code"]):
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
                    "identifier": {
                        "system": row.get('SITE_CODE_TYPE_URI', ''),
                        "value": row.get('SITE_CODE', '')
                    }
                }
            }
        ]
        fhir_json["performer"] = performer

        # Reason Code
        reason_code = {
            "coding": [
                {
                    "code": row.get('INDICATION_CODE', ''),
                    "system": "http://snomed.info/sct"
                }
            ]
        }
        if reason_code["coding"][0]["code"]:
            fhir_json["reasonCode"] = [reason_code]

        # Protocol Applied
        protocol_applied = {
            "targetDisease": map_target_disease(vaccine_type),
            "doseNumberPositiveInt": int(row.get('DOSE_SEQUENCE', 0))
        }
        fhir_json["protocolApplied"] = [protocol_applied]

        return fhir_json, True
    except KeyError as e:
        print(f"Missing field in row data: {e}")
        return None, False
    except ValueError as e:
        print(f"Value error in row data: {e}")
        return None, False
