import boto3
import unittest
import json
from unittest.mock import patch, MagicMock
from moto import mock_s3, mock_kinesis
from datetime import datetime
from src.constants import Constant
from io import StringIO, BytesIO
import csv


from batch_processing import main, validate_full_permissions


class TestLambdaHandler(unittest.TestCase):

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    @patch("batch_processing.validate_full_permissions")
    def test_e2e_successful_conversion(
        self, mock_validate_full_permissions, mock_csv_dict_reader, mock_send_to_kinesis
    ):
        # Mock S3 and Kinesis setup
        s3 = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        s3.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})

        # Create a mock Kinesis stream
        kinesis = boto3.client("kinesis", region_name="eu-west-2")
        stream_name = "imms-batch-internal-dev-processingdata-stream"
        kinesis.create_stream(StreamName=stream_name, ShardCount=1)

        # Define the mock response for the head_object method
        mock_head_object_response = {"LastModified": datetime(2024, 7, 30, 15, 22, 17)}
        mock_download_fileobj = Constant.mock_download_fileobj
        response = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": (
                        "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
                        "Immunization?immunization.identifier=https://supplierABC/identifiers/"
                        "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
                    ),
                }
            ],
            "entry": [
                {
                    "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
                    "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
                    "resource": {
                        "resourceType": "Immunization",
                        "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
                        "meta": {"versionId": 1},
                    },
                }
            ],
            "total": 1,
        }, 200

        vaccine_type = Constant.valid_vaccine_type[0]  # Example valid vaccine type
        supplier = Constant.valid_supplier[0]  # Example valid supplier
        ods_code = Constant.valid_ods_codes[0]  # Example valid ODS code

        with patch(
            "batch_processing.fetch_file_from_s3",
            return_value=Constant.string_return,
        ), patch(
            "batch_processing.s3_client.head_object",
            return_value=mock_head_object_response,
        ), patch(
            "batch_processing.ImmunizationApi.get_imms_id",
            return_value=response,
        ), patch(
            "batch_processing.s3_client.download_fileobj",
            return_value=mock_download_fileobj,
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance

            # Mock environment variables
            with patch.dict(
                "os.environ",
                {
                    "ENVIRONMENT": "internal-dev",
                    "LOCAL_ACCOUNT_ID": "123456",
                    "ACK_BUCKET_NAME": ack_bucket_name,
                    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
                    "KINESIS_STREAM_ARN": f"arn:aws:kinesis:eu-west-2:123456789012:stream/{stream_name}",
                },
            ):
                # Initialize the acknowledgment file with headers
                ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_" f"{ods_code}_20210730T12000000_response.csv"
                headers = Constant.header
                csv_buffer = StringIO()
                csv_writer = csv.writer(csv_buffer, delimiter="|")
                csv_writer.writerow(headers)
                csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))

                s3.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)
                mock_validate_full_permissions.return_value = True

                # Run the main function with the test event
                test_event = json.dumps(
                    {
                        "message_id": "123456",
                        "vaccine_type": vaccine_type,
                        "supplier": supplier,
                        "filename": f"{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
                    }
                )

                main(test_event)

                # Verify that the acknowledgment file has been updated in the destination bucket
                ack_file = s3.get_object(Bucket=ack_bucket_name, Key=ack_key)["Body"].read().decode("utf-8")

                self.assertIn("ok", ack_file)
                mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    @patch("batch_processing.validate_full_permissions")
    def test_e2e_successful_conversion_sqs_failed(
        self, mock_validate_full_permissions, mock_csv_dict_reader, mock_send_to_kinesis
    ):
        # Mock S3 and SQS setup
        s3 = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        s3.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        # Create a mock Kinesis stream
        kinesis = boto3.client("kinesis", region_name="eu-west-2")
        stream_name = "imms-batch-internal-dev-processingdata-stream"
        kinesis.create_stream(StreamName=stream_name, ShardCount=1)

        # Define the mock response for the head_object method
        mock_head_object_response = {"LastModified": datetime(2024, 7, 30, 15, 22, 17)}
        mock_download_fileobj = Constant.mock_download_fileobj
        response = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": (
                        "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
                        "Immunization?immunization.identifier=https://supplierABC/identifiers/"
                        "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
                    ),
                }
            ],
            "entry": [
                {
                    "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
                    "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
                    "resource": {
                        "resourceType": "Immunization",
                        "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
                        "meta": {"versionId": 1},
                    },
                }
            ],
            "total": 1,
        }, 200

        vaccine_type = Constant.valid_vaccine_type[0]  # Example valid vaccine type
        supplier = Constant.valid_supplier[0]  # Example valid supplier
        ods_code = Constant.valid_ods_codes[0]  # Example valid ODS code

        with patch(
            "batch_processing.fetch_file_from_s3",
            return_value=Constant.string_return,
        ), patch(
            "batch_processing.s3_client.head_object",
            return_value=mock_head_object_response,
        ), patch(
            "batch_processing.ImmunizationApi.get_imms_id",
            return_value=response,
        ), patch(
            "batch_processing.s3_client.download_fileobj",
            return_value=mock_download_fileobj,
        ), patch(
            "batch_processing.send_to_kinesis", return_value=False
        ):

            # Mock SQS and send a test message
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance

            # Mock environment variables
            with patch.dict(
                "os.environ",
                {
                    "ENVIRONMENT": "internal-dev",
                    "LOCAL_ACCOUNT_ID": "123456",
                    "ACK_BUCKET_NAME": ack_bucket_name,
                    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
                    "KINESIS_STREAM_ARN": f"arn:aws:kinesis:eu-west-2:123456789012:stream/{stream_name}",
                },
            ):
                # Initialize the acknowledgment file with headers
                ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_" f"{ods_code}_20210730T12000000_response.csv"
                headers = Constant.header
                csv_buffer = StringIO()
                csv_writer = csv.writer(csv_buffer, delimiter="|")
                csv_writer.writerow(headers)
                csv_buffer.seek(0)
                csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))

                s3.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)
                mock_validate_full_permissions.return_value = True
                # Run the main function with the test event
                test_event = json.dumps(
                    {
                        "message_id": "123456",
                        "vaccine_type": vaccine_type,
                        "supplier": supplier,
                        "filename": f"{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
                    }
                )

                main(test_event)

                # Verify that the acknowledgment file has been created in the destination bucket
                ack_file = s3.get_object(Bucket=ack_bucket_name, Key=ack_key)["Body"].read().decode("utf-8")

                self.assertIn("fatal-error", ack_file)
                mock_send_to_kinesis.assert_not_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    @patch("batch_processing.validate_full_permissions")
    def test_e2e_processing_invalid_data(
        self, mock_validate_full_permissions, mock_csv_dict_reader, mock_send_to_kinesis
    ):
        # Mock S3 and SQS setup
        s3 = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        s3.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        # Create a mock Kinesis stream
        kinesis = boto3.client("kinesis", region_name="eu-west-2")
        stream_name = "imms-batch-internal-dev-processingdata-stream"
        kinesis.create_stream(StreamName=stream_name, ShardCount=1)

        # Define the mock response for the head_object method
        mock_head_object_response = {"LastModified": datetime(2024, 7, 30, 15, 22, 17)}
        mock_download_fileobj = Constant.mock_download_fileobj
        response = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": (
                        "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
                        "Immunization?immunization.identifier=https://supplierABC/identifiers/"
                        "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
                    ),
                }
            ],
            "entry": [
                {
                    "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
                    "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
                    "resource": {
                        "resourceType": "Immunization",
                        "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
                        "meta": {"versionId": 1},
                    },
                }
            ],
            "total": 1,
        }, 200

        vaccine_type = Constant.valid_vaccine_type[0]  # Example valid vaccine type
        supplier = Constant.valid_supplier[0]  # Example valid supplier
        ods_code = Constant.valid_ods_codes[0]  # Example valid ODS code

        # Mock the fetch_file_from_s3 function
        with patch(
            "batch_processing.fetch_file_from_s3",
            return_value=Constant.invalid_file_content,
        ), patch(
            "batch_processing.convert_to_fhir_json",
            return_value={False, None},
        ), patch(
            "batch_processing.s3_client.head_object",
            return_value=mock_head_object_response,
        ), patch(
            "batch_processing.ImmunizationApi.get_imms_id",
            return_value=response,
        ), patch(
            "batch_processing.s3_client.download_fileobj",
            return_value=mock_download_fileobj,
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance

            # Mock environment variables
            with patch.dict(
                "os.environ",
                {
                    "ENVIRONMENT": "internal-dev",
                    "LOCAL_ACCOUNT_ID": "123456",
                    "ACK_BUCKET_NAME": ack_bucket_name,
                    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
                    "KINESIS_STREAM_ARN": f"arn:aws:kinesis:eu-west-2:123456789012:stream/{stream_name}",
                },
            ):
                # Initialize the acknowledgment file with headers
                ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_" f"{ods_code}_20210730T12000000_response.csv"
                headers = Constant.header
                csv_buffer = StringIO()
                csv_writer = csv.writer(csv_buffer, delimiter="|")
                csv_writer.writerow(headers)
                csv_buffer.seek(0)
                csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))

                s3.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)
                mock_validate_full_permissions.return_value = True
                # Run the main function with the test event
                test_event = json.dumps(
                    {
                        "message_id": "123456",
                        "vaccine_type": vaccine_type,
                        "supplier": supplier,
                        "filename": f"{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
                    }
                )

                main(test_event)

                # Verify that the acknowledgment file has been created in the destination bucket
                ack_file = s3.get_object(Bucket=ack_bucket_name, Key=ack_key)["Body"].read().decode("utf-8")

                self.assertIn("fatal-error", ack_file)
                mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    @patch("batch_processing.validate_full_permissions")
    def test_e2e_processing_imms_id_missing(
        self, mock_validate_full_permissions, mock_csv_dict_reader, mock_send_to_kinesis
    ):
        # Set up the S3 environment
        s3 = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        s3.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        # Create a mock Kinesis stream
        kinesis = boto3.client("kinesis", region_name="eu-west-2")
        stream_name = "imms-batch-internal-dev-processingdata-stream"
        kinesis.create_stream(StreamName=stream_name, ShardCount=1)
        # Define the mock response for the head_object method
        mock_head_object_response = {"LastModified": datetime(2024, 7, 30, 15, 22, 17)}
        mock_download_fileobj = Constant.mock_download_fileobj
        response = {"total": 0}, 404

        vaccine_type = Constant.valid_vaccine_type[0]  # Example valid vaccine type
        supplier = Constant.valid_supplier[0]  # Example valid supplier
        ods_code = Constant.valid_ods_codes[0]  # Example valid ODS code

        #   Mock the fetch_file_from_s3 function
        with patch("batch_processing.fetch_file_from_s3", return_value=Constant.string_update_return), patch(
            "batch_processing.s3_client.head_object", return_value=mock_head_object_response
        ), patch("batch_processing.ImmunizationApi.get_imms_id", return_value=response), patch(
            "batch_processing.s3_client.download_fileobj", return_value=mock_download_fileobj
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_update_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance

            # Mock environment variables
            with patch.dict(
                "os.environ",
                {
                    "ENVIRONMENT": "internal-dev",
                    "LOCAL_ACCOUNT_ID": "123456",
                    "ACK_BUCKET_NAME": ack_bucket_name,
                    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
                    "KINESIS_STREAM_ARN": f"arn:aws:kinesis:eu-west-2:123456789012:stream/{stream_name}",
                },
            ):

                # Initialize the acknowledgment file with headers
                ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_" f"{ods_code}_20210730T12000000_response.csv"
                headers = Constant.header
                csv_buffer = StringIO()
                csv_writer = csv.writer(csv_buffer, delimiter="|")
                csv_writer.writerow(headers)
                csv_buffer.seek(0)
                csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))

                s3.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)
                mock_validate_full_permissions.return_value = True
                # Run the lambda_handler function
                # Run the main function with the test event
                test_event = json.dumps(
                    {
                        "message_id": "123456",
                        "vaccine_type": vaccine_type,
                        "supplier": supplier,
                        "filename": f"{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
                    }
                )

                main(test_event)

            # Verify that the acknowledgment file has been created in S3
            ack_bucket = "immunisation-batch-internal-dev-data-destination"
            ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_" f"{ods_code}_20210730T12000000_response.csv"
            ack_file = s3.get_object(Bucket=ack_bucket, Key=ack_key)["Body"].read().decode("utf-8")
            self.assertIn("fatal-error", ack_file)
            self.assertIn("Unsupported file type received as an attachment", ack_file)
            mock_send_to_kinesis.assert_called()

    @mock_s3
    def test_validate_full_permissions_end_to_end(self):
        s3 = boto3.client("s3", region_name="eu-west-2")
        config_bucket_name = "test-bucket"
        s3.create_bucket(
            Bucket=config_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        permissions_data = {"all_permissions": {"DP": ["FLU_FULL"]}}
        s3.put_object(
            Bucket=config_bucket_name,
            Key="permissions.json",
            Body=json.dumps(permissions_data),
        )

        def mock_get_json_from_s3(config_bucket_name):
            return permissions_data

        with patch("batch_processing.get_json_from_s3", mock_get_json_from_s3):

            result = validate_full_permissions(config_bucket_name, "DP", "FLU")
            self.assertTrue(result)

            permissions_data["all_permissions"]["DP"] = ["FLU_CREATE"]
            result = validate_full_permissions(config_bucket_name, "dp", "FLU")
            self.assertFalse(result)

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("batch_processing.get_json_from_s3")
    @patch("csv.DictReader")
    def test_process_lambda_handler_permissions(
        self, mock_csv_dict_reader, mock_get_json_from_s3, mock_send_to_kinesis
    ):
        # Correct bucket creation with region specified
        s3_client = boto3.client("s3", region_name="eu-west-2")
        s3_client.create_bucket(Bucket="test-bucket", CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        s3_client.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})

        # Define the mock response for the head_object method
        mock_head_object_response = {"LastModified": datetime(2024, 7, 30, 15, 22, 17)}
        response = {"total": 0}, 404
        # Sample config data for supplier permissions
        config_data = {
            "all_permissions": {
                "TESTFULL": ["COVID19_FULL", "FLU_FULL", "MMR_FULL"],
                "TESTREDUCED": ["COVID19_FULL", "FLU_FULL", "MMR_FULL"],
                "supplierB": ["FLU_UPDATE", "FLU_DELETE"],
                "PINN": [""],
            },
            "definitions:": {
                "FULL": "Full permissions to create, update and delete a batch record",
                "CREATE": "Permission to create a batch record",
                "UPDATE": "Permission to update a batch record",
                "DELETE": "Permission to delete a batch record",
            },
        }
        mock_download_fileobj = Constant.mock_download_fileobj
        # Mock the get_json_from_s3 function to return the config data
        mock_get_json_from_s3.return_value = config_data

        # Create a mock Kinesis stream using moto
        kinesis = boto3.client("kinesis", region_name="eu-west-2")
        stream_name = "imms-batch-internal-dev-processingdata-stream"
        kinesis.create_stream(StreamName=stream_name, ShardCount=1)

        # Upload the mock CSV data to S3
        s3_client.put_object(
            Bucket="test-bucket",
            Key="Flu_Vaccinations_v5_YYY78_20240708T12130100.csv",
            Body="NHS_NUMBER|ACTION_FLAG|UNIQUE_ID_URI|UNIQUE_ID\n12345|update|"
            "urn:nhs:id|ID12345\n67890|delete|urn:nhs:id|ID67890",
        )

        vaccine_type = Constant.valid_vaccine_type[0]  # Example valid vaccine type
        supplier = Constant.valid_supplier[0]  # Example valid supplier
        ods_code = Constant.valid_ods_codes[0]  # Example valid ODS code

        #   Mock the fetch_file_from_s3 function
        with patch("batch_processing.fetch_file_from_s3", return_value=Constant.string_update_return), patch(
            "batch_processing.s3_client.head_object", return_value=mock_head_object_response
        ), patch("batch_processing.ImmunizationApi.get_imms_id", return_value=response), patch(
            "batch_processing.s3_client.download_fileobj", return_value=mock_download_fileobj
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_update_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance

            # Mock environment variables
            with patch.dict(
                "os.environ",
                {
                    "ENVIRONMENT": "internal-dev",
                    "LOCAL_ACCOUNT_ID": "123456",
                    "ACK_BUCKET_NAME": ack_bucket_name,
                    "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
                    "KINESIS_STREAM_ARN": f"arn:aws:kinesis:eu-west-2:123456789012:stream/{stream_name}",
                },
            ):

                # Initialize the acknowledgment file with headers
                ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_" f"{ods_code}_20210730T12000000_response.csv"
                headers = Constant.header
                csv_buffer = StringIO()
                csv_writer = csv.writer(csv_buffer, delimiter="|")
                csv_writer.writerow(headers)
                csv_buffer.seek(0)
                csv_bytes = BytesIO(csv_buffer.getvalue().encode("utf-8"))

                s3_client.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)
                # Run the lambda_handler function
                # Run the main function with the test event
                test_event = json.dumps(
                    {
                        "message_id": "123456",
                        "vaccine_type": vaccine_type,
                        "supplier": supplier,
                        "filename": f"{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
                    }
                )

                main(test_event)

            # Verify that the acknowledgment file has been created in S3
            ack_bucket = "immunisation-batch-internal-dev-data-destination"
            ack_key = f"processedFile/{vaccine_type}_Vaccinations_v5_" f"{ods_code}_20210730T12000000_response.csv"
            ack_file = s3_client.get_object(Bucket=ack_bucket, Key=ack_key)["Body"].read().decode("utf-8")
            self.assertIn("fatal-error", ack_file)
            self.assertIn("No permissions for operation", ack_file)
            mock_send_to_kinesis.assert_called()

    if __name__ == "__main__":
        unittest.main()
