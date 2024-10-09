from dataclasses import dataclass


class Constants:
    """A class to hold various constants used in the application."""

    ack_headers = [
        "MESSAGE_HEADER_ID",
        "HEADER_RESPONSE_CODE",
        "ISSUE_SEVERITY",
        "ISSUE_CODE",
        "RESPONSE_TYPE",
        "RESPONSE_CODE",
        "RESPONSE_DISPLAY",
        "RECEIVED_TIME",
        "MAILBOX_FROM",
        "LOCAL_ID",
        "MESSAGE_DELIVERY",
    ]

    mock_request_positive_string = [
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "new",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "test",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        }
    ]

    mock_request_only_mandatory = [
        {
            "NHS_NUMBER": "",
            "PERSON_FORENAME": "SABINA",
            "PERSON_SURNAME": "GREIR",
            "PERSON_DOB": "20190131",
            "PERSON_GENDER_CODE": "2",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "new",
            "PERFORMING_PROFESSIONAL_FORENAME": "",
            "PERFORMING_PROFESSIONAL_SURNAME": "",
            "RECORDED_DATE": "20240904T183325",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "",
            "DOSE_SEQUENCE": "",
            "VACCINE_PRODUCT_CODE": "",
            "VACCINE_PRODUCT_TERM": "",
            "VACCINE_MANUFACTURER": "",
            "BATCH_NUMBER": "",
            "EXPIRY_DATE": "",
            "SITE_OF_VACCINATION_CODE": "",
            "SITE_OF_VACCINATION_TERM": "",
            "ROUTE_OF_VACCINATION_CODE": "",
            "ROUTE_OF_VACCINATION_TERM": "",
            "DOSE_AMOUNT": "",
            "DOSE_UNIT_CODE": "",
            "DOSE_UNIT_TERM": "",
            "INDICATION_CODE": "",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        }
    ]
    mock_request_positive_string_missing = [
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "update",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        }
    ]
    mock_request = [
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "update",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "1",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        },
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "update",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "1",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        },
    ]

    mock_request_params_missing = [
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "1",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        },
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "update",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "1",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        },
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "",
            "ACTION_FLAG": "update",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "1",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        },
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "create",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "1",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        },
    ]
    mock_update_request = [
        {
            "NHS_NUMBER": "9732928395",
            "PERSON_FORENAME": "PHYLIS",
            "PERSON_SURNAME": "PEEL",
            "PERSON_DOB": "20080217",
            "PERSON_GENDER_CODE": "0",
            "PERSON_POSTCODE": "WD25 0DZ",
            "DATE_AND_TIME": "20240904T183325",
            "SITE_CODE": "RVVKC",
            "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
            "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
            "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
            "ACTION_FLAG": "update",
            "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
            "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
            "RECORDED_DATE": "20240904",
            "PRIMARY_SOURCE": "TRUE",
            "VACCINATION_PROCEDURE_CODE": "956951000000104",
            "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
            "DOSE_SEQUENCE": "1",
            "VACCINE_PRODUCT_CODE": "42223111000001107",
            "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
            "VACCINE_MANUFACTURER": "Sanofi Pasteur",
            "BATCH_NUMBER": "BN92478105653",
            "EXPIRY_DATE": "20240915",
            "SITE_OF_VACCINATION_CODE": "368209003",
            "SITE_OF_VACCINATION_TERM": "Right arm",
            "ROUTE_OF_VACCINATION_CODE": "1210999013",
            "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
            "DOSE_AMOUNT": "0.3",
            "DOSE_UNIT_CODE": "2622896019",
            "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
            "INDICATION_CODE": "1037351000000105",
            "LOCATION_CODE": "RJC02",
            "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        }
    ]
    request = {
        "NHS_NUMBER": "9732928395",
        "PERSON_FORENAME": "PHYLIS",
        "PERSON_SURNAME": "PEEL",
        "PERSON_DOB": "20080217",
        "PERSON_GENDER_CODE": "0",
        "PERSON_POSTCODE": "WD25 0DZ",
        "DATE_AND_TIME": "20240904T183325",
        "SITE_CODE": "RVVKC",
        "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        "UNIQUE_ID": "0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057",
        "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
        "ACTION_FLAG": "update",
        "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
        "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
        "RECORDED_DATE": "20240904",
        "PRIMARY_SOURCE": "TRUE",
        "VACCINATION_PROCEDURE_CODE": "956951000000104",
        "VACCINATION_PROCEDURE_TERM": "RSV vaccination in pregnancy (procedure)",
        "DOSE_SEQUENCE": "1",
        "VACCINE_PRODUCT_CODE": "42223111000001107",
        "VACCINE_PRODUCT_TERM": "Quadrivalent influenza vaccine (split virion, inactivated)",
        "VACCINE_MANUFACTURER": "Sanofi Pasteur",
        "BATCH_NUMBER": "BN92478105653",
        "EXPIRY_DATE": "20240915",
        "SITE_OF_VACCINATION_CODE": "368209003",
        "SITE_OF_VACCINATION_TERM": "Right arm",
        "ROUTE_OF_VACCINATION_CODE": "1210999013",
        "ROUTE_OF_VACCINATION_TERM": "Intradermal use",
        "DOSE_AMOUNT": "0.3",
        "DOSE_UNIT_CODE": "2622896019",
        "DOSE_UNIT_TERM": "Inhalation - unit of product usage",
        "INDICATION_CODE": "1037351000000105",
        "LOCATION_CODE": "RJC02",
        "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
    }

    test_permissions_config_file = {
        "all_permissions": {
            "DPFULL": ["COVID19_FULL", "FLU_FULL", "MMR_FULL"],
            "DPREDUCED": ["COVID19_FULL", "FLU_FULL", "MMR_FULL"],
            "SUPPLIER1": ["COVID19_CREATE", "COVID19_DELETE", "COVID19_UPDATE"],
            "SUPPLIER2": ["FLU_CREATE"],
            "EMIS": ["FLU_CREATE", "FLU_DELETE"],
            "SUPPLIER4": [""],
        },
        "definitions:": {
            "_FULL": "Full permissions to create, update and delete a batch record",
            "_CREATE": "Permission to create a batch record",
            "_UPDATE": "Permission to update a batch record",
            "_DELETE": "Permission to delete a batch record",
        },
    }

    file_content_operations = (
        "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
        "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
        "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
        "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
        "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
        "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
        "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
        "LOCATION_CODE|LOCATION_CODE_TYPE_URI\n"
        '"9732928395"|"PHYLIS"|"PEEL"|"20080217"|"0"|"WD25 0DZ"|"20240904T183325"|"RVVKC"|'
        '"https://fhir.nhs.uk/Id/ods-organization-code"|'
        '"0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057"|"https://www.ravs.england.nhs.uk/"|'
        '"new"|"Ellena"|"OReilly"|"20240904T183325"|'
        '"TRUE"|"956951000000104"|"RSV vaccination in pregnancy (procedure)"|"1"|"42223111000001107"|'
        '"Quadrivalent influenza vaccine (split virion)"|"Sanofi Pasteur"|'
        '"BN92478105653"|"20240915"|"368209003"|"Right arm"|"1210999013"|"Intradermal use"|"0.3"|'
        '"2622896019"|"Inhalation - unit of product usage"|"1037351000000105"|'
        '"RJC02"|"https://fhir.nhs.uk/Id/ods-organization-code"\n'
        '"9732928395"|"PHIL"|"PEL"|"20080217"|"0"|"WD25 0DZ"|"20240904T183325"|"RVVKC"|'
        '"https://fhir.nhs.uk/Id/ods-organization-code"|'
        '"0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057"|"https://www.ravs.england.nhs.uk/"|'
        '"delete"|"Ellena"|"OReilly"|"20240904T183325"|'
        '"TRUE"|"956951000000104"|"RSV vaccination in pregnancy (procedure)"|"1"|"42223111000001107"|'
        '"Quadrivalent influenza vaccine (split virion)"|"Sanofi Pasteur"|'
        '"BN92478105653"|"20240915"|"368209003"|"Right arm"|"1210999013"|"Intradermal use"|"0.3"|'
        '"2622896019"|"Inhalation - unit of product usage"|"1037351000000105"|'
        '"RJC02"|"https://fhir.nhs.uk/Id/ods-organization-code"\n'
    )


@dataclass
class DiseaseCodes:
    """Disease Codes"""

    covid_19: str = "840539006"
    flu: str = "6142004"
    measles: str = "14189004"
    mumps: str = "36989005"
    rubella: str = "36653000"


class DiseaseDisplayTerms:
    """Disease display terms which correspond to disease codes"""

    covid_19: str = "Disease caused by severe acute respiratory syndrome coronavirus 2"
    flu: str = "Influenza"
    measles: str = "Measles"
    mumps: str = "Mumps"
    rubella: str = "Rubella"


vaccine_disease_mapping = {
    "covid19": ["covid_19"],
    "flu": ["flu"],
    "mmr": ["measles", "mumps", "rubella"],
}


def map_target_disease(vaccine_type):
    # Retrieve the disease types associated with the vaccine
    diseases = vaccine_disease_mapping.get(vaccine_type, [])

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
