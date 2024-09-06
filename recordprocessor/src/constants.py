class Constant:
    """A class to hold various constants used in the application."""

    valid_vaccine_type = ["flu", "covid19", "mmr"]
    valid_versions = ["v5"]
    valid_ods_codes = [
        "YGM41",
        "8J1100001",
        "8HK48",
        "YGA",
        "0DE",
        "0DF",
        "8HA94",
        "X26",
        "YGMYH",
        "W00",
        "W000",
        "ZT001",
        "YA7",
        "N2N9I",
        "YGJ",
        "DPSREDUCED",
        "DPSFULL",
    ]
    valid_supplier = [
        "EMIS",
        "PINNACLE",
        "SONAR",
        "TPP",
        "AGEM-NIVS",
        "NIMS",
        "EVA",
        "RAVS",
        "MEDICAL_DIRECTOR",
        "WELSH_DA_1",
        "WELSH_DA_2",
        "NORTHERN_IRELAND_DA",
        "SCOTLAND_DA",
        "COVID19_VACCINE_RESOLUTION_SERVICEDESK",
        "EMIS",
    ]
    headers = [
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

    header = [
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

    mock_download_fileobj = (
        "MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|RESPONSE_TYPE|"
        "RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID|,MESSAGE_DELIVERY"
    )

    expected_csv_content = [
        "NHS_NUMBER",
        "PERSON_FORENAME",
        "PERSON_SURNAME",
        "PERSON_DOB",
        "PERSON_GENDER_CODE",
        "PERSON_POSTCODE",
        "DATE_AND_TIME",
        "SITE_CODE",
        "SITE_CODE_TYPE_URI",
        "UNIQUE_ID",
        "UNIQUE_ID_URI",
        "ACTION_FLAG",
        "PERFORMING_PROFESSIONAL_FORENAME",
        "PERFORMING_PROFESSIONAL_SURNAME",
        "RECORDED_DATE",
        "PRIMARY_SOURCE",
        "VACCINATION_PROCEDURE_CODE",
        "VACCINATION_PROCEDURE_TERM",
        "DOSE_SEQUENCE",
        "VACCINE_PRODUCT_CODE",
        "VACCINE_PRODUCT_TERM",
        "VACCINE_MANUFACTURER",
        "BATCH_NUMBER",
        "EXPIRY_DATE",
        "SITE_OF_VACCINATION_CODE",
        "SITE_OF_VACCINATION_TERM",
        "ROUTE_OF_VACCINATION_CODE",
        "ROUTE_OF_VACCINATION_TERM",
        "DOSE_AMOUNT",
        "DOSE_UNIT_CODE",
        "DOSE_UNIT_TERM",
        "INDICATION_CODE",
        "LOCATION_CODE",
        "LOCATION_CODE_TYPE_URI",
    ]

    invalid_csv_content = (
        "INVALID_HEADER1,INVALID_HEADER2,INVALID_HEADER3,INVALID_HEADER4,INVALID_HEADER5,"
        "INVALID_HEADER6,INVALID_HEADER7,INVALID_HEADER8,INVALID_HEADER9,INVALID_HEADER10,"
        "INVALID_HEADER11,INVALID_HEADER12,INVALID_HEADER13,INVALID_HEADER14,INVALID_HEADER15,"
        "INVALID_HEADER16,INVALID_HEADER17,INVALID_HEADER18,INVALID_HEADER19,INVALID_HEADER20,"
        "INVALID_HEADER21,INVALID_HEADER22,INVALID_HEADER23,INVALID_HEADER24,INVALID_HEADER25,"
        "INVALID_HEADER26,INVALID_HEADER27,INVALID_HEADER28,INVALID_HEADER29,INVALID_HEADER30,"
        "INVALID_HEADER31,INVALID_HEADER32,INVALID_HEADER33,INVALID_HEADER34"
    )

    file_content = (
        "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
        "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
        "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
        "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
        "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
        "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
        "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
        "LOCATION_CODE|LOCATION_CODE_TYPE_URI\n"
        '9674963871|"SABINA"|"GREIR"|"20190131"|"2"|"GU14 6TU"|"20240610T183325"|"J82067"|'
        '"https://fhir.nhs.uk/Id/ods-organization-code"|"0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"|'
        '"https://www.ravs.england.nhs.uk/"|"new"|"Ellena"|"O\'Reilly"|"20240609"|"TRUE"|'
        '"1303503001"|"Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"|'
        '1|"42605811000001109"|"Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) '
        '(product)"|"Pfizer"|"RSVTEST"|"20241231"|"368208006"|"Left upper arm structure (body structure)"|'
        '"78421000"|"Intramuscular route (qualifier value)"|"0.5"|"258773002"|"Milliliter (qualifier value)"|"Test"|'
        '"J82067"|"https://fhir.nhs.uk/Id/ods-organization-code"\n'
        '1234567890|"JOHN"|"DOE"|"19801231"|"1"|"AB12 3CD"|"20240611T120000"|"J82068"|'
        '"https://fhir.nhs.uk/Id/ods-organization-code"|"0002_COVID19_v1_DOSE_1"|"https://www.ravs.england.nhs.uk/"|'
        '"update"|"Jane"|"Smith"|"20240610"|"FALSE"|"1324657890"|'
        '"Administration of COVID-19 vaccine product (procedure)"|'
        '1|"1234567890"|'
        '"Comirnaty 0.3ml dose concentrate for dispersion for injection multidose vials (Pfizer/BioNTech) '
        '(product)"|"Pfizer/BioNTech"|"COVIDBATCH"|"20250101"|"368208007"|"Right upper arm structure (body structure)"|'
        '"385219009"|"Intramuscular route (qualifier value)"|'
        '"0.3"|"258773002"|"Milliliter (qualifier value)"|"Routine"|'
        '"J82068"|"https://fhir.nhs.uk/Id/ods-organization-code"'
    )

    file_content_id_missing = (
        "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|DATE_AND_TIME|"
        "SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|PERFORMING_PROFESSIONAL_FORENAME|"
        "PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|"
        "VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|"
        "VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|"
        "ROUTE_OF_VACCINATION_CODE|ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|"
        "INDICATION_CODE|LOCATION_CODE|LOCATION_CODE_TYPE_URI\n"
        '9674963871|"SABINA"|"GREIR"|"20190131"|"2"|"GU14 6TU"|"20240610T183325"|"J82067"|'
        '"https://fhir.nhs.uk/Id/ods-organization-code"|"0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"|'
        '"https://www.ravs.england.nhs.uk/"|"update"|"Ellena"|"O\'Reilly"|"20240609"|"TRUE"|'
        '"1303503001"|"Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"|'
        '1|"42605811000001109"|"Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) '
        '(product)"|"Pfizer"|"RSVTEST"|"20241231"|"368208006"|"Left upper arm structure (body structure)"|'
        '"78421000"|"Intramuscular route (qualifier value)"|"0.5"|"258773002"|"Milliliter (qualifier value)"|"Test"|'
        '"J82067"|"https://fhir.nhs.uk/Id/ods-organization-code"\n'
        '1234567890|"JOHN"|"DOE"|"19801231"|"1"|"AB12 3CD"|"20240611T120000"|"J82068"|'
        '"https://fhir.nhs.uk/Id/ods-organization-code"|"0002_COVID19_v1_DOSE_1"|"https://www.ravs.england.nhs.uk/"|'
        '"delete"|"Jane"|"Smith"|"20240610"|"FALSE"|"1324657890"|'
        '"Administration of COVID-19 vaccine product (procedure)"|'
        '1|"1234567890"|'
        '"Comirnaty 0.3ml dose concentrate for dispersion for injection multidose vials (Pfizer/BioNTech) '
        '(product)"|"Pfizer/BioNTech"|"COVIDBATCH"|"20250101"|"368208007"|"Right upper arm structure (body structure)"|'
        '"385219009"|"Intramuscular route (qualifier value)"|"0.3"|"258773002"|'
        '"Milliliter (qualifier value)"|"Routine"|'
        '"J82068"|"https://fhir.nhs.uk/Id/ods-organization-code"'
    )

    invalid_file_content = (
        "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
        "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
        "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
        "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
        "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
        "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
        "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
        "LOCATION_CODE|LOCATION_CODE_TYPE_URI\n"
        '9674963871|"SABINA"|"GREIR"|"20190131"|"2"|"GU14 6TU"|"20240610T183325"|"J82067"|'
        '"https://fhir.nhs.uk/Id/ods-organization-code"|"0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"|'
        '"https://www.ravs.england.nhs.uk/"|"new"|"Ellena"|"O\'Reilly"|"20240609"|"TRUE"|'
        '"1303503001"|"Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"|'
        '1|"42605811000001109"|"Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) '
        '(product)"|"Pfizer"|"RSVTEST"|"20241231"|"368208006"|"Left upper arm structure (body structure)"|'
        '"78421000"|"Intramuscular route (qualifier value)"|"0.5"|"258773002"|"Milliliter (qualifier value)"|'
        '""|"J82067"|"https://fhir.nhs.uk/Id/ods-organization-code"'
    )

    row = {
        "NHS_NUMBER": "9674963871",
        "PERSON_FORENAME": "SABINA",
        "PERSON_SURNAME": "GREIR",
        "PERSON_DOB": "20190131",
        "PERSON_GENDER_CODE": "2",
        "PERSON_POSTCODE": "GU14 6TU",
        "DATE_AND_TIME": "20240610T183325",
        "SITE_CODE": "J82067",
        "SITE_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
        "UNIQUE_ID": "0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1",
        "UNIQUE_ID_URI": "https://www.ravs.england.nhs.uk/",
        "ACTION_FLAG": "new",
        "PERFORMING_PROFESSIONAL_FORENAME": "Ellena",
        "PERFORMING_PROFESSIONAL_SURNAME": "O'Reilly",
        "RECORDED_DATE": "20240609",
        "PRIMARY_SOURCE": "TRUE",
        "VACCINATION_PROCEDURE_CODE": "1303503001",
        "VACCINATION_PROCEDURE_TERM": (
            "Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"
        ),
        "DOSE_SEQUENCE": "1",
        "VACCINE_PRODUCT_CODE": "42605811000001109",
        "VACCINE_PRODUCT_TERM": (
            "Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) (product)"
        ),
        "VACCINE_MANUFACTURER": "Pfizer",
        "BATCH_NUMBER": "RSVTEST",
        "EXPIRY_DATE": "20241231",
        "SITE_OF_VACCINATION_CODE": "368208006",
        "SITE_OF_VACCINATION_TERM": "Left upper arm structure (body structure)",
        "ROUTE_OF_VACCINATION_CODE": "78421000",
        "ROUTE_OF_VACCINATION_TERM": "Intramuscular route (qualifier value)",
        "DOSE_AMOUNT": "0.5",
        "DOSE_UNIT_CODE": "258773002",
        "DOSE_UNIT_TERM": "Milliliter (qualifier value)",
        "INDICATION_CODE": "None",
        "INDICATION_TERM": "none",  # Not provided
        "LOCATION_CODE": "J82067",
        "LOCATION_CODE_TYPE_URI": "https://fhir.nhs.uk/Id/ods-organization-code",
    }

    string_return = (
        "NHS_NUMBER|1234567890|John|Doe|2000-01-01|M|SW1A 1AA|2022-01-01T10:00:00|123456|"
        "https://nhs.uk|ABC123|https://supplierABC|new|Dr|Smith|2022-01-01|true|procedureCode|"
        "procedureTerm|1|productCode|productTerm|manufacturer|batchNumber|2023-01-01|siteCode|"
        "siteTerm|routeCode|routeTerm|0.5|ml|code|location|https://locationUri"
    )
    string_update_return = (
        "NHS_NUMBER|1234567890|John|Doe|2000-01-01|M|SW1A 1AA|2022-01-01T10:00:00|123456|"
        "https://nhs.uk|ABC123|https://supplierABC|new|Dr|Smith|2022-01-01|true|procedureCode|"
        "procedureTerm|1|productCode|productTerm|manufacturer|batchNumber|2023-01-01|siteCode|"
        "siteTerm|routeCode|routeTerm|0.5|ml|code|location|https://locationUri"
    )
    mock_request_positive_string = [
        {
            'NHS_NUMBER': '9732928395',
            'PERSON_FORENAME': 'PHYLIS',
            'PERSON_SURNAME': 'PEEL',
            'PERSON_DOB': '20080217',
            'PERSON_GENDER_CODE': '0',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057',
            'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
            'ACTION_FLAG': 'new',
            'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
            'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
            'RECORDED_DATE': '20240904',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': 'RSV vaccination in pregnancy (procedure)',
            'DOSE_SEQUENCE': 'test',
            'VACCINE_PRODUCT_CODE': '42223111000001107',
            'VACCINE_PRODUCT_TERM': 'Quadrivalent influenza vaccine (split virion, inactivated)',
            'VACCINE_MANUFACTURER': 'Sanofi Pasteur',
            'BATCH_NUMBER': 'BN92478105653',
            'EXPIRY_DATE': '20240915',
            'SITE_OF_VACCINATION_CODE': '368209003',
            'SITE_OF_VACCINATION_TERM': 'Right arm',
            'ROUTE_OF_VACCINATION_CODE': '1210999013',
            'ROUTE_OF_VACCINATION_TERM': 'Intradermal use',
            'DOSE_AMOUNT': '0.3',
            'DOSE_UNIT_CODE': '2622896019',
            'DOSE_UNIT_TERM': 'Inhalation - unit of product usage',
            'INDICATION_CODE': '1037351000000105',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        }
    ]

    mock_request_only_mandatory = [
        {
            'NHS_NUMBER': '',
            'PERSON_FORENAME': 'SABINA',
            'PERSON_SURNAME': 'GREIR',
            'PERSON_DOB': '20190131',
            'PERSON_GENDER_CODE': '2',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057',
            'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
            'ACTION_FLAG': 'new',
            'PERFORMING_PROFESSIONAL_FORENAME': '',
            'PERFORMING_PROFESSIONAL_SURNAME': '',
            'RECORDED_DATE': '20240904T183325',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': '',
            'DOSE_SEQUENCE': '',
            'VACCINE_PRODUCT_CODE': '',
            'VACCINE_PRODUCT_TERM': '',
            'VACCINE_MANUFACTURER': '',
            'BATCH_NUMBER': '',
            'EXPIRY_DATE': '',
            'SITE_OF_VACCINATION_CODE': '',
            'SITE_OF_VACCINATION_TERM': '',
            'ROUTE_OF_VACCINATION_CODE': '',
            'ROUTE_OF_VACCINATION_TERM': '',
            'DOSE_AMOUNT': '',
            'DOSE_UNIT_CODE': '',
            'DOSE_UNIT_TERM': '',
            'INDICATION_CODE': '',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        }
    ]
    mock_request_positive_string_missing = [
        {
            'NHS_NUMBER': '9732928395',
            'PERSON_FORENAME': 'PHYLIS',
            'PERSON_SURNAME': 'PEEL',
            'PERSON_DOB': '20080217',
            'PERSON_GENDER_CODE': '0',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057',
            'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
            'ACTION_FLAG': 'update',
            'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
            'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
            'RECORDED_DATE': '20240904',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': 'RSV vaccination in pregnancy (procedure)',
            'DOSE_SEQUENCE': '',
            'VACCINE_PRODUCT_CODE': '42223111000001107',
            'VACCINE_PRODUCT_TERM': 'Quadrivalent influenza vaccine (split virion, inactivated)',
            'VACCINE_MANUFACTURER': 'Sanofi Pasteur',
            'BATCH_NUMBER': 'BN92478105653',
            'EXPIRY_DATE': '20240915',
            'SITE_OF_VACCINATION_CODE': '368209003',
            'SITE_OF_VACCINATION_TERM': 'Right arm',
            'ROUTE_OF_VACCINATION_CODE': '1210999013',
            'ROUTE_OF_VACCINATION_TERM': 'Intradermal use',
            'DOSE_AMOUNT': '0.3',
            'DOSE_UNIT_CODE': '2622896019',
            'DOSE_UNIT_TERM': 'Inhalation - unit of product usage',
            'INDICATION_CODE': '1037351000000105',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        }
    ]
    mock_request = [
        {
            'NHS_NUMBER': '9732928395',
            'PERSON_FORENAME': 'PHYLIS',
            'PERSON_SURNAME': 'PEEL',
            'PERSON_DOB': '20080217',
            'PERSON_GENDER_CODE': '0',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057',
            'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
            'ACTION_FLAG': 'update',
            'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
            'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
            'RECORDED_DATE': '20240904',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': 'RSV vaccination in pregnancy (procedure)',
            'DOSE_SEQUENCE': '1',
            'VACCINE_PRODUCT_CODE': '42223111000001107',
            'VACCINE_PRODUCT_TERM': 'Quadrivalent influenza vaccine (split virion, inactivated)',
            'VACCINE_MANUFACTURER': 'Sanofi Pasteur',
            'BATCH_NUMBER': 'BN92478105653',
            'EXPIRY_DATE': '20240915',
            'SITE_OF_VACCINATION_CODE': '368209003',
            'SITE_OF_VACCINATION_TERM': 'Right arm',
            'ROUTE_OF_VACCINATION_CODE': '1210999013',
            'ROUTE_OF_VACCINATION_TERM': 'Intradermal use',
            'DOSE_AMOUNT': '0.3',
            'DOSE_UNIT_CODE': '2622896019',
            'DOSE_UNIT_TERM': 'Inhalation - unit of product usage',
            'INDICATION_CODE': '1037351000000105',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        }
    ]

    mock_request_params_missing = [
        {
            'NHS_NUMBER': '9732928395',
            'PERSON_FORENAME': 'PHYLIS',
            'PERSON_SURNAME': 'PEEL',
            'PERSON_DOB': '20080217',
            'PERSON_GENDER_CODE': '0',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057',
            'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
            'ACTION_FLAG': '',
            'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
            'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
            'RECORDED_DATE': '20240904',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': 'RSV vaccination in pregnancy (procedure)',
            'DOSE_SEQUENCE': '1',
            'VACCINE_PRODUCT_CODE': '42223111000001107',
            'VACCINE_PRODUCT_TERM': 'Quadrivalent influenza vaccine (split virion, inactivated)',
            'VACCINE_MANUFACTURER': 'Sanofi Pasteur',
            'BATCH_NUMBER': 'BN92478105653',
            'EXPIRY_DATE': '20240915',
            'SITE_OF_VACCINATION_CODE': '368209003',
            'SITE_OF_VACCINATION_TERM': 'Right arm',
            'ROUTE_OF_VACCINATION_CODE': '1210999013',
            'ROUTE_OF_VACCINATION_TERM': 'Intradermal use',
            'DOSE_AMOUNT': '0.3',
            'DOSE_UNIT_CODE': '2622896019',
            'DOSE_UNIT_TERM': 'Inhalation - unit of product usage',
            'INDICATION_CODE': '1037351000000105',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        },
        {
            'NHS_NUMBER': '9732928395',
            'PERSON_FORENAME': 'PHYLIS',
            'PERSON_SURNAME': 'PEEL',
            'PERSON_DOB': '20080217',
            'PERSON_GENDER_CODE': '0',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '',
            'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
            'ACTION_FLAG': 'update',
            'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
            'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
            'RECORDED_DATE': '20240904',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': 'RSV vaccination in pregnancy (procedure)',
            'DOSE_SEQUENCE': '1',
            'VACCINE_PRODUCT_CODE': '42223111000001107',
            'VACCINE_PRODUCT_TERM': 'Quadrivalent influenza vaccine (split virion, inactivated)',
            'VACCINE_MANUFACTURER': 'Sanofi Pasteur',
            'BATCH_NUMBER': 'BN92478105653',
            'EXPIRY_DATE': '20240915',
            'SITE_OF_VACCINATION_CODE': '368209003',
            'SITE_OF_VACCINATION_TERM': 'Right arm',
            'ROUTE_OF_VACCINATION_CODE': '1210999013',
            'ROUTE_OF_VACCINATION_TERM': 'Intradermal use',
            'DOSE_AMOUNT': '0.3',
            'DOSE_UNIT_CODE': '2622896019',
            'DOSE_UNIT_TERM': 'Inhalation - unit of product usage',
            'INDICATION_CODE': '1037351000000105',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        },
        {
            'NHS_NUMBER': '9732928395',
            'PERSON_FORENAME': 'PHYLIS',
            'PERSON_SURNAME': 'PEEL',
            'PERSON_DOB': '20080217',
            'PERSON_GENDER_CODE': '0',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057',
            'UNIQUE_ID_URI': '',
            'ACTION_FLAG': 'update',
            'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
            'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
            'RECORDED_DATE': '20240904',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': 'RSV vaccination in pregnancy (procedure)',
            'DOSE_SEQUENCE': '1',
            'VACCINE_PRODUCT_CODE': '42223111000001107',
            'VACCINE_PRODUCT_TERM': 'Quadrivalent influenza vaccine (split virion, inactivated)',
            'VACCINE_MANUFACTURER': 'Sanofi Pasteur',
            'BATCH_NUMBER': 'BN92478105653',
            'EXPIRY_DATE': '20240915',
            'SITE_OF_VACCINATION_CODE': '368209003',
            'SITE_OF_VACCINATION_TERM': 'Right arm',
            'ROUTE_OF_VACCINATION_CODE': '1210999013',
            'ROUTE_OF_VACCINATION_TERM': 'Intradermal use',
            'DOSE_AMOUNT': '0.3',
            'DOSE_UNIT_CODE': '2622896019',
            'DOSE_UNIT_TERM': 'Inhalation - unit of product usage',
            'INDICATION_CODE': '1037351000000105',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        },
        {
            'NHS_NUMBER': '9732928395',
            'PERSON_FORENAME': 'PHYLIS',
            'PERSON_SURNAME': 'PEEL',
            'PERSON_DOB': '20080217',
            'PERSON_GENDER_CODE': '0',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057',
            'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
            'ACTION_FLAG': 'create',
            'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
            'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
            'RECORDED_DATE': '20240904',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': 'RSV vaccination in pregnancy (procedure)',
            'DOSE_SEQUENCE': '1',
            'VACCINE_PRODUCT_CODE': '42223111000001107',
            'VACCINE_PRODUCT_TERM': 'Quadrivalent influenza vaccine (split virion, inactivated)',
            'VACCINE_MANUFACTURER': 'Sanofi Pasteur',
            'BATCH_NUMBER': 'BN92478105653',
            'EXPIRY_DATE': '20240915',
            'SITE_OF_VACCINATION_CODE': '368209003',
            'SITE_OF_VACCINATION_TERM': 'Right arm',
            'ROUTE_OF_VACCINATION_CODE': '1210999013',
            'ROUTE_OF_VACCINATION_TERM': 'Intradermal use',
            'DOSE_AMOUNT': '0.3',
            'DOSE_UNIT_CODE': '2622896019',
            'DOSE_UNIT_TERM': 'Inhalation - unit of product usage',
            'INDICATION_CODE': '1037351000000105',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        }
    ]
    mock_update_request = [
        {
            'NHS_NUMBER': '9732928395',
            'PERSON_FORENAME': 'PHYLIS',
            'PERSON_SURNAME': 'PEEL',
            'PERSON_DOB': '20080217',
            'PERSON_GENDER_CODE': '0',
            'PERSON_POSTCODE': 'WD25 0DZ',
            'DATE_AND_TIME': '20240904T183325',
            'SITE_CODE': 'RVVKC',
            'SITE_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code',
            'UNIQUE_ID': '0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057',
            'UNIQUE_ID_URI': 'https://www.ravs.england.nhs.uk/',
            'ACTION_FLAG': 'update',
            'PERFORMING_PROFESSIONAL_FORENAME': 'Ellena',
            'PERFORMING_PROFESSIONAL_SURNAME': "O'Reilly",
            'RECORDED_DATE': '20240904',
            'PRIMARY_SOURCE': 'TRUE',
            'VACCINATION_PROCEDURE_CODE': '956951000000104',
            'VACCINATION_PROCEDURE_TERM': 'RSV vaccination in pregnancy (procedure)',
            'DOSE_SEQUENCE': '1',
            'VACCINE_PRODUCT_CODE': '42223111000001107',
            'VACCINE_PRODUCT_TERM': 'Quadrivalent influenza vaccine (split virion, inactivated)',
            'VACCINE_MANUFACTURER': 'Sanofi Pasteur',
            'BATCH_NUMBER': 'BN92478105653',
            'EXPIRY_DATE': '20240915',
            'SITE_OF_VACCINATION_CODE': '368209003',
            'SITE_OF_VACCINATION_TERM': 'Right arm',
            'ROUTE_OF_VACCINATION_CODE': '1210999013',
            'ROUTE_OF_VACCINATION_TERM': 'Intradermal use',
            'DOSE_AMOUNT': '0.3',
            'DOSE_UNIT_CODE': '2622896019',
            'DOSE_UNIT_TERM': 'Inhalation - unit of product usage',
            'INDICATION_CODE': '1037351000000105',
            'LOCATION_CODE': 'RJC02',
            'LOCATION_CODE_TYPE_URI': 'https://fhir.nhs.uk/Id/ods-organization-code'
        }
    ]

    action_flag_mapping = {"NEW": "CREATE", "UPDATE": "UPDATE", "DELETE": "DELETE"}

    def data_rows(status, created_at_formatted):

        if status is True:
            data_row = ['TBC', 'ok', 'information', 'informational', 'business',
                        '20013', 'Success', created_at_formatted, 'TBC', 'DPS', True]
            return data_row
        elif status == "None":
            data_row = ['TBC', 'fatal-error', 'error', 'error', 'business', '20005', 'Unsupported file type received as an attachment', created_at_formatted, 'TBC', 'DPS', True]  # noqa: E501
            return data_row
        else:
            data_row = [
                "TBC",
                "fatal-error",
                "error",
                "error",
                "business",
                "20005",
                "Unsupported file type received as an attachment",
                created_at_formatted,
                "TBC",
                "DPS",
                False,
            ]  # noqa: E501
            return data_row
