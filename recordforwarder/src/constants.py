class Constant:
    """A class to hold various constants used in the application."""

    header = [
        'MESSAGE_HEADER_ID', 'HEADER_RESPONSE_CODE', 'ISSUE_SEVERITY', 'ISSUE_CODE',
        'RESPONSE_TYPE', 'RESPONSE_CODE', 'RESPONSE_DISPLAY', 'RECEIVED_TIME',
        'MAILBOX_FROM', 'LOCAL_ID', 'MESSAGE_DELIVERY'
    ]

    test_fhir_json = {
        "resourceType": "Immunization",
        "contained": [
            {
                "resourceType": "Practitioner",
                "id": "Pract1",
                "name": [
                    {
                        "family": "Doe",
                        "given": ["Jane"]
                    }
                ]
            },
            {
                "resourceType": "Patient",
                "id": "Pat1",
                "identifier": [
                    {
                        "system": "https://fhir.nhs.uk/Id/nhs-number",
                        "value": "1234567890"
                    }
                ],
                "name": [
                    {
                        "family": "SMITH",
                        "given": ["JOHN"]
                    }
                ],
                "gender": "male",
                "birthDate": "2000-01-01",
                "address": [
                    {
                        "postalCode": "AB12 3CD"
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
                            "code": "123456789",
                            "display": "Administration of vaccine product containing only Dummy antigen (procedure)"
                        }
                    ]
                }
            }
        ],
        "identifier": [
            {
                "system": "https://www.ravs.england.nhs.uk/",
                "value": "0001_TEST_v1_RUN_1_ABCD-123_Dose_seq_01"
            }
        ],
        "status": "completed",
        "vaccineCode": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "987654321",
                    "display": "Dummy vaccine powder and solvent for solution (product)"
                }
            ]
        },
        "patient": {
            "reference": "#Pat1"
        },
        "occurrenceDateTime": "2024-01-01T00:00:00+00:00",
        "recorded": "2024-01-01T00:00:00+00:00",
        "primarySource": True,
        "manufacturer": {
            "display": "Dummy Pharma"
        },
        "location": {
            "type": "Location",
            "identifier": {
                "value": "ABCDE",
                "system": "https://fhir.nhs.uk/Id/ods-organization-code"
            }
        },
        "lotNumber": "DUMMYLOT",
        "expirationDate": "2024-12-31",
        "site": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "999999999",
                    "display": "Right upper arm structure (body structure)"
                }
            ]
        },
        "route": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "111111111",
                    "display": "Subcutaneous route (qualifier value)"
                }
            ]
        },
        "doseQuantity": {
            "system": "http://snomed.info/sct",
            "value": 0.5,
            "unit": "Milliliter (qualifier value)",
            "code": "123456789"
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
                        "system": "https://fhir.nhs.uk/Id/ods-organization-code",
                        "value": "DUMMYORG"
                    }
                }
            }
        ],
        "reasonCode": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "dummy"
                    }
                ]
            }
        ],
        "protocolApplied": [
            {
                "targetDisease": [
                    {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "123456789",
                                "display": "Dummy disease caused by dummy virus"
                            }
                        ]
                    }
                ],
                "doseNumberPositiveInt": 1
            }
        ]
    }

    def data_rows(status, created_at_formatted):

        if status is True:
            data_row = ['TBC', 'ok', 'information', 'informational', 'business',
                        '20013', 'Success', created_at_formatted, 'TBC', 'DPS', True]
            return data_row
        elif status == "duplicate":
            data_row = ['TBC', 'fatal-error', 'error', 'error', 'business',
                        '20007', 'Duplicate Message received', created_at_formatted, 'TBC', 'DPS', False]
            return data_row
        else:
            data_row = ['TBC', 'fatal-error', 'error', 'error', 'business', '20009', 'Payload validation failure', created_at_formatted, 'TBC', 'DPS', False]  # noqa: E501
            return data_row
