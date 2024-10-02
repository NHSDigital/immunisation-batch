# """File of values which can be used for testing"""

# # Dictionary for mocking the os.environ dict
# MOCK_ENVIRONMENT_DICT = {
#     "ENVIRONMENT": "internal-dev",
#     "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
#     "LOCAL_ACCOUNT_ID": "123456789012",
#     "PROD_ACCOUNT_ID": "3456789109",
#     "CONFIG_BUCKET_NAME": "immunisation-batch-internal-dev-config",
# }

# SOURCE_BUCKET_NAME = "immunisation-batch-internal-dev-data-source"
# DESTINATION_BUCKET_NAME = "immunisation-batch-internal-dev-data-destination"

# VALID_FLU_EMIS_FILE_KEY = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
# VALID_FLU_EMIS_ACK_FILE_KEY = "ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_response.csv"

# SQS_ATTRIBUTES = {"FifoQueue": "true", "ContentBasedDeduplication": "true"}


# VALID_FILE_CONTENT = (
#     "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
#     "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
#     "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
#     "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
#     "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
#     "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
#     "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
#     "LOCATION_CODE|LOCATION_CODE_TYPE_URI\n"
#     '9674963871|"SABINA"|"GREIR"|"20190131"|"2"|"GU14 6TU"|"20240610T183325"|"J82067"|'
#     '"https://fhir.nhs.uk/Id/ods-organization-code"|"0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"|'
#     '"https://www.ravs.england.nhs.uk/"|"new"|"Ellena"|"O\'Reilly"|"20240609"|"TRUE"|'
#     '"1303503001"|"Administration of vaccine product containing only Human orthopneumovirus antigen (procedure)"|'
#     '1|"42605811000001109"|"Abrysvo vaccine powder and solvent for solution for injection 0.5ml vials (Pfizer Ltd) '
#     '(product)"|"Pfizer"|"RSVTEST"|"20241231"|"368208006"|"Left upper arm structure (body structure)"|'
#     '"78421000"|"Intramuscular route (qualifier value)"|"0.5"|"258773002"|"Milliliter (qualifier value)"|"Test"|'
#     '"J82067"|"https://fhir.nhs.uk/Id/ods-organization-code"\n'
#     '1234567890|"JOHN"|"DOE"|"19801231"|"1"|"AB12 3CD"|"20240611T120000"|"J82068"|'
#     '"https://fhir.nhs.uk/Id/ods-organization-code"|"0002_COVID19_v1_DOSE_1"|"https://www.ravs.england.nhs.uk/"|'
#     '"update"|"Jane"|"Smith"|"20240610"|"FALSE"|"1324657890"|'
#     '"Administration of COVID-19 vaccine product (procedure)"|'
#     '1|"1234567890"|'
#     '"Comirnaty 0.3ml dose concentrate for dispersion for injection multidose vials (Pfizer/BioNTech) '
#     '(product)"|"Pfizer/BioNTech"|"COVIDBATCH"|"20250101"|"368208007"|"Right upper arm structure (body structure)"|'
#     '"385219009"|"Intramuscular route (qualifier value)"|'
#     '"0.3"|"258773002"|"Milliliter (qualifier value)"|"Routine"|'
#     '"J82068"|"https://fhir.nhs.uk/Id/ods-organization-code"'
# )

# FILE_CONTENT_WITH_NEW_AND_DELETE_ACTION_FLAGS = (
#     "NHS_NUMBER|PERSON_FORENAME|PERSON_SURNAME|PERSON_DOB|PERSON_GENDER_CODE|PERSON_POSTCODE|"
#     "DATE_AND_TIME|SITE_CODE|SITE_CODE_TYPE_URI|UNIQUE_ID|UNIQUE_ID_URI|ACTION_FLAG|"
#     "PERFORMING_PROFESSIONAL_FORENAME|PERFORMING_PROFESSIONAL_SURNAME|RECORDED_DATE|"
#     "PRIMARY_SOURCE|VACCINATION_PROCEDURE_CODE|VACCINATION_PROCEDURE_TERM|DOSE_SEQUENCE|"
#     "VACCINE_PRODUCT_CODE|VACCINE_PRODUCT_TERM|VACCINE_MANUFACTURER|BATCH_NUMBER|EXPIRY_DATE|"
#     "SITE_OF_VACCINATION_CODE|SITE_OF_VACCINATION_TERM|ROUTE_OF_VACCINATION_CODE|"
#     "ROUTE_OF_VACCINATION_TERM|DOSE_AMOUNT|DOSE_UNIT_CODE|DOSE_UNIT_TERM|INDICATION_CODE|"
#     "LOCATION_CODE|LOCATION_CODE_TYPE_URI\n"
#     '"9732928395"|"PHYLIS"|"PEEL"|"20080217"|"0"|"WD25 0DZ"|"20240904T183325"|"RVVKC"|'
#     '"https://fhir.nhs.uk/Id/ods-organization-code"|'
#     '"0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057"|"https://www.ravs.england.nhs.uk/"|'
#     '"new"|"Ellena"|"OReilly"|"20240904T183325"|'
#     '"TRUE"|"956951000000104"|"RSV vaccination in pregnancy (procedure)"|"1"|"42223111000001107"|'
#     '"Quadrivalent influenza vaccine (split virion)"|"Sanofi Pasteur"|'
#     '"BN92478105653"|"20240915"|"368209003"|"Right arm"|"1210999013"|"Intradermal use"|"0.3"|'
#     '"2622896019"|"Inhalation - unit of product usage"|"1037351000000105"|'
#     '"RJC02"|"https://fhir.nhs.uk/Id/ods-organization-code"\n'
#     '"9732928395"|"PHIL"|"PEL"|"20080217"|"0"|"WD25 0DZ"|"20240904T183325"|"RVVKC"|'
#     '"https://fhir.nhs.uk/Id/ods-organization-code"|'
#     '"0001_RSV_v5_Run3_valid_dose_1_new_upd_del_20240905130057"|"https://www.ravs.england.nhs.uk/"|'
#     '"delete"|"Ellena"|"OReilly"|"20240904T183325"|'
#     '"TRUE"|"956951000000104"|"RSV vaccination in pregnancy (procedure)"|"1"|"42223111000001107"|'
#     '"Quadrivalent influenza vaccine (split virion)"|"Sanofi Pasteur"|'
#     '"BN92478105653"|"20240915"|"368209003"|"Right arm"|"1210999013"|"Intradermal use"|"0.3"|'
#     '"2622896019"|"Inhalation - unit of product usage"|"1037351000000105"|'
#     '"RJC02"|"https://fhir.nhs.uk/Id/ods-organization-code"\n'
# )


# # DON'T DELETE THIS EVENT - IT MAY BE USED FOR FUTURE TESTING
# EVENT = {
#     "Records": [
#         {
#             "eventVersion": "2.1",
#             "eventSource": "aws:s3",
#             "awsRegion": "eu-west-2",
#             "eventTime": "2024-07-09T12:00:00Z",
#             "eventName": "ObjectCreated:Put",
#             "userIdentity": {"principalId": "AWS:123456789012:user/Admin"},
#             "requestParameters": {"sourceIPAddress": "127.0.0.1"},
#             "responseElements": {
#                 "x-amz-request-id": "EXAMPLE123456789",
#                 "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH",
#             },
#             "s3": {
#                 "s3SchemaVersion": "1.0",
#                 "configurationId": "testConfigRule",
#                 "bucket": {
#                     "name": "test-bucket",
#                     "ownerIdentity": {"principalId": "EXAMPLE"},
#                     "arn": "arn:aws:s3:::example-bucket",
#                 },
#                 "object": {
#                     "key": "FLU_Vaccinations_v5_YGM41_20240708T12130100.csv",
#                     "size": 1024,
#                     "eTag": "5",
#                     "sequencer": "0A1B2C3D4E5F678901",
#                 },
#             },
#         }
#     ]
# }
