# import boto3
# import unittest
# import json
# from unittest.mock import patch, MagicMock
# from moto import mock_s3, mock_kinesis
# from datetime import datetime
# from src.constants import Constant
# from io import StringIO, BytesIO
# import csv
# from batch_processing import main, validate_full_permissions


# class TestLambdaHandler(unittest.TestCase):

#     def setUp(self):
#         # Start mock services
#         self.mock_s3 = mock_s3()
#         self.mock_kinesis = mock_kinesis()
#         self.mock_s3.start()
#         self.mock_kinesis.start()

#         # Ensure no session conflicts
#         boto3.setup_default_session()

#         self.region = "eu-west-2"
#         self.s3_client = boto3.client("s3", region_name=self.region)
#         self.kinesis_client = boto3.client("kinesis", region_name=self.region)

#         self.bucket_name = "immunisation-batch-internal-dev-data-sources"
#         self.ack_bucket_name = "immunisation-batch-internal-dev-data-destinations"
#         self.stream_name = "imms-batch-internal-dev-processingdata-stream"
#         # Set up S3 buckets
#         self.s3_client.create_bucket(
#             Bucket=self.bucket_name,
#             CreateBucketConfiguration={"LocationConstraint": self.region},
#         )
#         self.s3_client.create_bucket(
#             Bucket=self.ack_bucket_name,
#             CreateBucketConfiguration={"LocationConstraint": self.region},
#         )

#         # Set up Kinesis stream
#         self.kinesis_client.create_stream(StreamName=self.stream_name, ShardCount=1)

#         self.mock_head_object_response = {"LastModified": datetime(2024, 7, 30, 15, 22, 17)}
#         self.mock_download_fileobj = Constant.mock_download_fileobj
#         self.response = {
#             "resourceType": "Bundle",
#             "type": "searchset",
#             "link": [
#                 {
#                     "relation": "self",
#                     "url": (
#                         "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
#                         "Immunization?immunization.identifier=https://supplierABC/identifiers/"
#                         "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
#                     ),
#                 }
#             ],
#             "entry": [
#                 {
#                     "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
#                     "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
#                     "resource": {
#                         "resourceType": "Immunization",
#                         "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
#                         "meta": {"versionId": 1},
#                     },
#                 }
#             ],
#             "total": 1,
#         }, 200
#         self.vaccine_type = Constant.valid_vaccine_type[2]
#         self.supplier = Constant.valid_supplier[0]
#         self.ods_code = Constant.valid_ods_codes[0]
#         self.test_event_base = {
#             "message_id": "123456",
#             "vaccine_type": None,
#             "supplier": None,
#             "filename": None,
#         }
#         self.mock_headers = Constant.header

#     def setup_acknowledgment_file(self, vaccine_type, ods_code):
#         ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000_response.csv"
#         csv_buffer = StringIO()
#         csv_writer = csv.writer(csv_buffer, delimiter="|")
#         csv_writer.writerow(self.mock_headers)
#         csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))
#         self.s3_client.upload_fileobj(csv_bytes, self.ack_bucket_name, ack_key)
#         return ack_key

#     def acknowledgment_file(self, vaccine_type, ods_code):
#         ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000_response.csv"
#         return ack_key

#     @patch("batch_processing.send_to_kinesis")
#     @patch("csv.DictReader")
#     @patch("batch_processing.validate_full_permissions")
#     @patch("batch_processing.fetch_file_from_s3")
#     @patch("batch_processing.s3_client.head_object")
#     @patch("batch_processing.ImmunizationApi.get_imms_id")
#     @patch("batch_processing.s3_client.download_fileobj")
#     def execute_test(
#         self,
#         mock_download_fileobj,
#         mock_get_imms_id,
#         mock_head_object,
#         mock_fetch_file,
#         mock_validate_full_permissions,
#         mock_csv_dict_reader,
#         mock_send_to_kinesis,
#         expected_ack_content,
#         fetch_file_content,
#         get_imms_id_response,
#         test_event_filename,
#         kinesis
#     ):

#         mock_fetch_file.return_value = fetch_file_content
#         mock_head_object.return_value = self.mock_head_object_response
#         mock_get_imms_id.return_value = get_imms_id_response
#         mock_download_fileobj.return_value = self.mock_download_fileobj
#         mock_validate_full_permissions.return_value = True
#         if kinesis:
#             mock_send_to_kinesis.return_value = True
#         else:
#             mock_send_to_kinesis.return_value = False
#         mock_csv_reader_instance = MagicMock()
#         mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
#         mock_csv_dict_reader.return_value = mock_csv_reader_instance

#         with patch.dict(
#             "os.environ",
#             {
#                 "ENVIRONMENT": "internal-dev",
#                 "LOCAL_ACCOUNT_ID": "123456",
#                 "ACK_BUCKET_NAME": self.ack_bucket_name,
#                 "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
#                 "KINESIS_STREAM_ARN": f"arn:aws:kinesis:{self.region}:123456789012:stream/{self.stream_name}",
#             },
#         ):
#             self.setup_acknowledgment_file(self.vaccine_type, self.ods_code)

#             test_event = json.dumps(
#                 {
#                     **self.test_event_base,
#                     "vaccine_type": self.vaccine_type,
#                     "supplier": self.supplier,
#                     "filename": test_event_filename.format(vaccine_type=self.vaccine_type, ods_code=self.ods_code),
#                 }
#             )

#             main(test_event)

#             response = self.s3_client.get_object(
#                 Bucket=self.ack_bucket_name, Key=self.acknowledgment_file(self.vaccine_type, self.ods_code)
#             )
#             content = response["Body"].read().decode("utf-8")

#             self.assertIn(expected_ack_content, content)
#             mock_send_to_kinesis.assert_called()

#     def test_e2e_successful_conversion(self):
#         self.execute_test(
#             expected_ack_content="ok",
#             fetch_file_content=Constant.string_return,
#             get_imms_id_response=self.response,
#             test_event_filename="{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
#             kinesis=True
#         )

#     @patch("batch_processing.convert_to_fhir_json")
#     def test_e2e_processing_invalid_data(self, mock_convert_json):
#         mock_convert_json.return_value = None, False
#         self.execute_test(
#             expected_ack_content="fatal-error",
#             fetch_file_content=Constant.invalid_file_content,
#             get_imms_id_response=self.response,
#             test_event_filename="{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
#             kinesis=True
#         )

#     def test_e2e_processing_imms_id_missing(self):
#         response = {"total": 0}, 404
#         self.execute_test(
#             expected_ack_content="fatal-error",
#             fetch_file_content=Constant.string_update_return,
#             get_imms_id_response=response,
#             test_event_filename="{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
#             kinesis=True
#         )

#     def test_e2e_successful_conversion_kinesis_failed(self):
#         self.execute_test(
#             expected_ack_content="fatal-error",
#             fetch_file_content=Constant.string_return,
#             get_imms_id_response=self.response,
#             test_event_filename="{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
#             kinesis=False
#         )

#     @mock_s3
#     def test_validate_full_permissions_end_to_end(self):
#         config_bucket_name = "test-bucket"
#         self.s3_client.create_bucket(
#             Bucket=config_bucket_name,
#             CreateBucketConfiguration={"LocationConstraint": self.region},
#         )

#         permissions_data = {"all_permissions": {"DP": ["FLU_FULL"]}}
#         self.s3_client.put_object(
#             Bucket=config_bucket_name,
#             Key="permissions.json",
#             Body=json.dumps(permissions_data),
#         )

#         def mock_get_json_from_s3(config_bucket_name):
#             return permissions_data

#         with patch("batch_processing.get_json_from_s3", mock_get_json_from_s3):
#             result = validate_full_permissions(config_bucket_name, "DP", "FLU")
#             self.assertTrue(result)

#             permissions_data["all_permissions"]["DP"] = ["FLU_CREATE"]
#             result = validate_full_permissions(config_bucket_name, "DP", "FLU")
#             self.assertFalse(result)


# if __name__ == "__main__":
#     unittest.main()
