from datetime import datetime, timezone
import re


class EmptyFieldException(Exception):
    """Custom exception raised when a required field is empty."""
    pass


def convert_to_fhir_json(row, vaccine_type):

    vaccine_type = vaccine_type.lower()

    def convert_to_iso_datetime(date_time, has_time=False):
        if not date_time:
            raise EmptyFieldException("Date field cannot be empty.")

        is_date_time_without_timezone = re.compile(r"\d{8}T\d{6}").fullmatch(date_time)
        is_date_time_utc = re.compile(r"\d{8}T\d{6}00").fullmatch(date_time)
        is_date_time_bst = re.compile(r"\d{8}T\d{6}01").fullmatch(date_time)

        try:
            if is_date_time_utc:
                return datetime.strptime(date_time, "%Y%m%dT%H%M%S00").strftime("%Y-%m-%dT%H:%M:%S+00:00")

            if is_date_time_bst:
                return datetime.strptime(date_time, "%Y%m%dT%H%M%S01").strftime("%Y-%m-%dT%H:%M:%S+01:00")

            if is_date_time_without_timezone:
                return datetime.strptime(date_time, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")

            # Handle date without time
            if not has_time:
                return datetime.strptime(date_time, "%Y%m%d").date().isoformat()

        except ValueError:
            raise EmptyFieldException(f"Invalid date format: {date_time}")

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
            raise EmptyFieldException(f"Unsupported vaccine type: {vaccine_type}")

    def convert_to_boolean(value):
        if value.lower() == 'true':
            return True
        elif value.lower() == 'false':
            return False
        else:
            raise EmptyFieldException(f"Invalid boolean value: {value}")

    def map_gender(gender_code):
        gender_map = {
            "1": "male",
            "2": "female",
            "9": "other",
            "0": "unknown"
        }
        if not gender_code:
            raise EmptyFieldException("Gender field cannot be empty.")
        return gender_map.get(gender_code, "unknown")

    try:
        # Check all fields in the row for empty values
        for key, value in row.items():
            if value == '':
                raise EmptyFieldException(f"The field {key} cannot be empty.")

        fhir_json = {
            "resourceType": "Immunization",
            "contained": [
                {
                    "resourceType": "Practitioner",
                    "id": "Pract1",
                    "name": [
                        {
                            "family": row['PERFORMING_PROFESSIONAL_SURNAME'],
                            "given": [row['PERFORMING_PROFESSIONAL_FORENAME']]
                        }
                    ]
                },
                {
                    "resourceType": "Patient",
                    "id": "Pat1",
                    "identifier": [
                        {
                            "system": "https://fhir.nhs.uk/Id/nhs-number",
                            "value": row['NHS_NUMBER']
                        }
                    ],
                    "name": [
                        {
                            "family": row['PERSON_SURNAME'],
                            "given": [row['PERSON_FORENAME']]
                        }
                    ],
                    "gender": map_gender(row['PERSON_GENDER_CODE']),
                    "birthDate": convert_to_iso_datetime(row['PERSON_DOB']),
                    "address": [
                        {
                            "postalCode": row['PERSON_POSTCODE']
                        }
                    ]
                }
            ],
            "extension": [
                {
                    "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-VaccinationProcedure",
                    "valueCodeableConcept": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": row['VACCINATION_PROCEDURE_CODE'],
                                "display": row['VACCINATION_PROCEDURE_TERM']
                            }
                        ]
                    }
                }
            ],
            "identifier": [
                {
                    "system": row['UNIQUE_ID_URI'],
                    "value": row['UNIQUE_ID']
                }
            ],
            "status": "completed",
            "vaccineCode": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": row['VACCINE_PRODUCT_CODE'],
                        "display": row['VACCINE_PRODUCT_TERM']
                    }
                ]
            },
            "patient": {
                "reference": "#Pat1"
            },
            "occurrenceDateTime": convert_to_iso_datetime(row['DATE_AND_TIME'], has_time=True),
            "recorded": convert_to_iso_datetime(row['RECORDED_DATE']),
            "primarySource": convert_to_boolean(row['PRIMARY_SOURCE']),
            "manufacturer": {
                "display": row['VACCINE_MANUFACTURER']
            },
            "location": {
                "type": "Location",
                "identifier": {
                    "value": row['LOCATION_CODE'],
                    "system": row['LOCATION_CODE_TYPE_URI']
                }
            },
            "lotNumber": row['BATCH_NUMBER'],
            "expirationDate": convert_to_iso_datetime(row['EXPIRY_DATE']),  # Convert to YYYY-MM-DD
            "site": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": row['SITE_OF_VACCINATION_CODE'],
                        "display": row['SITE_OF_VACCINATION_TERM']
                    }
                ]
            },
            "route": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": row['ROUTE_OF_VACCINATION_CODE'],
                        "display": row['ROUTE_OF_VACCINATION_TERM']
                    }
                ]
            },
            "doseQuantity": {
                "value": float(row['DOSE_AMOUNT']),
                "unit": row['DOSE_UNIT_TERM'],
                "system": "http://unitsofmeasure.org",
                "code": row['DOSE_UNIT_CODE']
            },
            "performer": [
                {
                    "actor": {
                        "reference": "#Pract1"
                    }
                },
                {
                    "actor": {
                        "type": "Organization",
                        "identifier": {
                            "system": row['SITE_CODE_TYPE_URI'],
                            "value": row['SITE_CODE']
                        }
                    }
                }
            ],
            "reasonCode": [
                {
                    "coding": [
                        {
                            "code": row['INDICATION_CODE'],
                            "system": "http://snomed.info/sct"
                        }
                    ]
                }
            ],
            "protocolApplied": [
                {
                    "targetDisease": map_target_disease(vaccine_type),
                    "doseNumberPositiveInt": int(row['DOSE_SEQUENCE'])
                }
            ]
        }
        return fhir_json, True
    except KeyError as e:
        print(f"Missing field in row data: {e}")
        return None, False
    except ValueError as e:
        print(f"Value error in row data: {e}")
        return None, False
    except EmptyFieldException as e:
        print(f"Empty field error: {e}")
        return None, False
