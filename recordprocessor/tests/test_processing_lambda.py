import unittest
from unittest.mock import patch, MagicMock
import boto3

# from io import BytesIO
from moto import mock_s3, mock_sqs
from src.constants import Constant
import json
from processing_lambda import (
    process_lambda_handler,
    fetch_file_from_s3,
    process_csv_to_fhir,
    get_environment,
    validate_full_permissions,
    get_supplier_permissions,
    get_permission_operations,
)


class TestProcessLambdaFunction(unittest.TestCase):
    @patch("processing_lambda.sqs_client")
    @patch("processing_lambda.process_csv_to_fhir")
    @patch("processing_lambda.boto3.client")
    @patch("processing_lambda.validate_full_permissions")
    def test_lambda_handler(
        self,
        mock_validate_full_permissions,
        mock_boto_client,
        mock_process_csv_to_fhir,
        mock_sqs_client,
    ):
        # Mock SQS client.
        mock_sqs_client_instance = MagicMock()
        mock_sqs_client.return_value = mock_sqs_client_instance

        # Mock S3 client.
        mock_s3_client_instance = MagicMock()
        mock_boto_client.return_value = mock_s3_client_instance

        mock_validate_full_permissions.return_value = True

        # Set up the queue URL and message body.
        message_body = {
            "vaccine_type": "COVID19",
            "supplier": "Pfizer",
            "filename": "testfile.csv",
        }

        # Mock SQS receive_message to return a predefined message
        mock_sqs_client_instance.receive_message.return_value = {
            "Messages": [
                {
                    "MessageId": "1",
                    "ReceiptHandle": "dummy-receipt-handle",
                    "Body": json.dumps(message_body),
                }
            ]
        }

        # Patch environment variables
        with patch.dict(
            "os.environ",
            {
                "SOURCE_BUCKET_NAME": "source-bucket",
                "PROD_ACCOUNT_ID": "123456789012",
                "LOCAL_ACCOUNT_ID": "local-123",
                "ENVIRONMENT": "internal-dev",
                "ACK_BUCKET_NAME": "ack-bucket",
            },
        ):
            # Invoke the lambda handler
            event = {"Records": [{"body": json.dumps(message_body)}]}
            process_lambda_handler(event, {})

            # Assert process_csv_to_fhir was called with correct arguments
            mock_process_csv_to_fhir.assert_called_once_with(
                "source-bucket",
                "testfile.csv",
                "Pfizer",
                "COVID19",
                "ack-bucket",
                True,
                set(),
            )

    @mock_s3
    def test_fetch_file_from_s3(self):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"

        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body="test content")

        with patch("processing_lambda.s3_client", s3_client):
            content = fetch_file_from_s3(bucket_name, file_key)
            self.assertEqual(content, "test content")

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir(self, mock_csv_dict_reader, mock_send_to_sqs):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=Constant.file_content
        )
        results = {
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
        with patch(
            "processing_lambda.ImmunizationApi.get_imms_id", return_value=results
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(
                bucket_name, file_key, supplier, "covid19", ack_bucket_name, "True", ""
            )

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_positive_string_provided(
        self, mock_csv_dict_reader, mock_send_to_sqs
    ):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = True
        permission_operations = set()
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=Constant.file_content
        )
        results = {
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
        with patch(
            "processing_lambda.ImmunizationApi.get_imms_id", return_value=results
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(
                Constant.mock_request_positive_string
            )
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(
                bucket_name,
                file_key,
                supplier,
                "covid19",
                ack_bucket_name,
                full_permissions,
                permission_operations,
            )

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("Success", content)
        mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_only_mandatory(
        self, mock_csv_dict_reader, mock_send_to_sqs
    ):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = True
        permission_operations = set()

        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=Constant.file_content
        )
        results = {
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
        with patch(
            "processing_lambda.ImmunizationApi.get_imms_id", return_value=results
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(
                Constant.mock_request_only_mandatory
            )
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(
                bucket_name,
                file_key,
                supplier,
                "covid19",
                ack_bucket_name,
                full_permissions,
                permission_operations,
            )

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("Success", content)
        mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_positive_string_not_provided(
        self, mock_csv_dict_reader, mock_send_to_sqs
    ):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = True
        permission_operations = set()
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=Constant.file_content
        )
        results = {
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
        with patch(
            "processing_lambda.ImmunizationApi.get_imms_id", return_value=results
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(
                Constant.mock_request_positive_string_missing
            )
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(
                bucket_name,
                file_key,
                supplier,
                "covid19",
                ack_bucket_name,
                full_permissions,
                permission_operations,
            )

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("Success", content)
        mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_invalid(self, mock_csv_dict_reader, mock_send_to_sqs):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = True
        permission_operations = set()
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=Constant.file_content
        )
        with patch("processing_lambda.convert_to_fhir_json", return_value=({}, False)):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(
                bucket_name,
                file_key,
                supplier,
                Constant.valid_vaccine_type[1],
                ack_bucket_name,
                full_permissions,
                permission_operations,
            )

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("fatal-error", content)
        mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_paramter_missing(
        self, mock_csv_dict_reader, mock_send_to_sqs
    ):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = True
        permission_operations = set()
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=Constant.file_content
        )
        with patch("processing_lambda.convert_to_fhir_json", return_value=({}, True)):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(
                Constant.mock_request_params_missing
            )
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(
                bucket_name,
                file_key,
                supplier,
                Constant.valid_vaccine_type[1],
                ack_bucket_name,
                full_permissions,
                permission_operations,
            )

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("fatal-error", content)
        mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_failed(self, mock_csv_dict_reader, mock_send_to_sqs):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = True
        permission_operations = set()

        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(
            Bucket=bucket_name, Key=file_key, Body=Constant.file_content_id_missing
        )
        results = {"total": 0}, 400
        with patch(
            "processing_lambda.convert_to_fhir_json", return_value=({}, True)
        ), patch("processing_lambda.ImmunizationApi.get_imms_id", return_value=results):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(
                Constant.mock_update_request
            )
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(
                bucket_name,
                file_key,
                supplier,
                "covid19",
                ack_bucket_name,
                full_permissions,
                permission_operations,
            )

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("fatal-error", content)
        mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_successful(
        self, mock_csv_dict_reader, mock_send_to_sqs
    ):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = True
        permission_operations = set()
        csv_content = Constant.file_content
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=csv_content)
        results = {
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
        vaccine_types = Constant.valid_vaccine_type
        for vaccine_type in vaccine_types:
            with patch(
                "processing_lambda.ImmunizationApi.get_imms_id", return_value=results
            ):
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance.__iter__.return_value = iter(
                    Constant.mock_update_request
                )
                mock_csv_dict_reader.return_value = mock_csv_reader_instance
                process_csv_to_fhir(
                    bucket_name,
                    file_key,
                    supplier,
                    vaccine_type,
                    ack_bucket_name,
                    full_permissions,
                    permission_operations,
                )

            ack_filename = "processedFile/test-file_response.csv"
            response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
            content = response["Body"].read().decode("utf-8")
            self.assertIn("Success", content)
            mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_successful_permissions(
        self, mock_csv_dict_reader, mock_send_to_sqs
    ):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test_file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = None
        permission_operations = {"CREATE", "NEW", "UPDATE"}
        csv_content = Constant.file_content_operations
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=csv_content)
        results = {
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
        vaccine_types = Constant.valid_vaccine_type
        for vaccine_type in vaccine_types:
            with patch(
                "processing_lambda.ImmunizationApi.get_imms_id", return_value=results
            ):
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance.__iter__.return_value = iter(
                    Constant.mock_update_request
                )
                mock_csv_dict_reader.return_value = mock_csv_reader_instance
                process_csv_to_fhir(
                    bucket_name,
                    file_key,
                    supplier,
                    vaccine_type,
                    ack_bucket_name,
                    full_permissions,
                    permission_operations,
                )

            ack_filename = "processedFile/test_file_response.csv"
            response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
            content = response["Body"].read().decode("utf-8")
            self.assertIn("Success", content)
            mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch("processing_lambda.send_to_sqs")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_incorrect_permissions(
        self, mock_csv_dict_reader, mock_send_to_sqs
    ):
        s3_client = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-bucket"
        file_key = "test_file.csv"
        supplier = "test"
        ack_bucket_name = "ack-bucket"
        full_permissions = None
        permission_operations = {"DELETE"}
        csv_content = Constant.file_content
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=csv_content)
        results = {
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
        vaccine_types = Constant.valid_vaccine_type
        for vaccine_type in vaccine_types:
            with patch(
                "processing_lambda.ImmunizationApi.get_imms_id", return_value=results
            ):
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance.__iter__.return_value = iter(
                    Constant.mock_update_request
                )
                mock_csv_dict_reader.return_value = mock_csv_reader_instance
                process_csv_to_fhir(
                    bucket_name,
                    file_key,
                    supplier,
                    vaccine_type,
                    ack_bucket_name,
                    full_permissions,
                    permission_operations,
                )

            mock_send_to_sqs.assert_not_called()

    def test_get_environment(self):
        with patch("processing_lambda.os.getenv", return_value="internal-dev"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

        with patch("processing_lambda.os.getenv", return_value="prod"):
            env = get_environment()
            self.assertEqual(env, "prod")

        with patch("processing_lambda.os.getenv", return_value="unknown-env"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

    @patch("processing_lambda.get_supplier_permissions")
    def test_no_permissions(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = [""]
        config_bucket_name = "test-bucket"
        supplier = "test-supplier"
        vaccine_type = "COVID19"

        result = validate_full_permissions(config_bucket_name, supplier, vaccine_type)

        self.assertFalse(result)

    @patch("processing_lambda.get_json_from_s3")
    def test_get_supplier_permissions_success(self, mock_get_json_from_s3):
        # Mock S3 response
        mock_get_json_from_s3.return_value = Constant.test_permissions_config_file

        supplier = "SUPPLIER1"
        config_bucket_name = "test-config-bucket"

        permissions = get_supplier_permissions(supplier, config_bucket_name)

        self.assertEqual(
            permissions, ["COVID19_CREATE", "COVID19_DELETE", "COVID19_UPDATE"]
        )

    @patch("processing_lambda.get_json_from_s3")
    def test_get_supplier_permissions_no_permissions(self, mock_get_json_from_s3):
        mock_get_json_from_s3.return_value = Constant.test_permissions_config_file

        supplier = "SUPPLIER4"
        config_bucket_name = "test-config-bucket"

        permissions = get_supplier_permissions(supplier, config_bucket_name)

        self.assertEqual(permissions, [""])

    @patch("processing_lambda.get_supplier_permissions")
    def test_validate_full_permissions_valid(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["FLU_FULL", "MMR_CREATE"]

        supplier = "supplier1"
        config_bucket_name = "test-config-bucket"
        vaccine_type = "FLU"

        result = validate_full_permissions(config_bucket_name, supplier, vaccine_type)

        self.assertTrue(result)

    @patch("processing_lambda.get_supplier_permissions")
    def test_validate_full_permissions_invalid(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["COVID19_CREATE"]

        supplier = "supplier1"
        config_bucket_name = "test-config-bucket"
        vaccine_type = "COVID19"

        result = validate_full_permissions(config_bucket_name, supplier, vaccine_type)

        self.assertFalse(result)

    @patch("processing_lambda.get_supplier_permissions")
    def test_get_permission_operations_success(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = [
            "MMR_FULL",
            "FLU_CREATE",
            "FLU_UPDATE",
        ]

        supplier = "supplier1"
        config_bucket_name = "test-config-bucket"
        vaccine_type = "FLU"

        operations = get_permission_operations(
            supplier, config_bucket_name, vaccine_type
        )

        self.assertEqual(operations, {"CREATE", "UPDATE", "NEW"})

    @patch("processing_lambda.get_supplier_permissions")
    def test_get_permission_operations_one_permission(
        self, mock_get_supplier_permissions
    ):
        mock_get_supplier_permissions.return_value = ["MMR_UPDATE"]

        supplier = "supplier1"
        config_bucket_name = "test-config-bucket"
        vaccine_type = "MMR"

        operations = get_permission_operations(
            supplier, config_bucket_name, vaccine_type
        )

        self.assertEqual(operations, {"UPDATE"})


if __name__ == "__main__":
    unittest.main()
