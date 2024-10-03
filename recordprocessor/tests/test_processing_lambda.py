import unittest
from unittest.mock import patch, MagicMock
import boto3

# from io import BytesIO
from moto import mock_s3, mock_kinesis
from src.constants import Constants
import json
from batch_processing import (
    main,
    fetch_file_from_s3,
    process_csv_to_fhir,
    get_environment,
    get_supplier_permissions,
    get_action_flag_permissions,
    convert_to_fhir_json,
)


class TestProcessLambdaFunction(unittest.TestCase):
    @patch("batch_processing.process_csv_to_fhir")
    @patch("batch_processing.get_action_flag_permissions")
    def test_lambda_handler(
        self,
        mock_get_action_flag_permissions,
        mock_process_csv_to_fhir,
    ):

        mock_get_action_flag_permissions.return_value = {"NEW", "UPDATE", "DELETE"}

        # Set up the queue URL and message body.
        message_body = {"vaccine_type": "COVID19", "supplier": "Pfizer", "filename": "testfile.csv"}

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
            main(json.dumps(message_body))

            # Assert process_csv_to_fhir was called with correct arguments
            mock_process_csv_to_fhir.assert_called_once_with(
                file_key="testfile.csv",
                supplier="Pfizer",
                vaccine_type="COVID19",
                message_id=None,
                permission_operations={"NEW", "UPDATE", "DELETE"},
            )

    @mock_s3
    def test_fetch_file_from_s3(self):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "test-bucket"
        file_key = "test-file.csv"

        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body="test content")

        with patch("batch_processing.s3_client", s3_client):
            content = fetch_file_from_s3(bucket_name, file_key)
            self.assertEqual(content, "test content")

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        s3_client.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constants.file_content)
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
        with patch("batch_processing.ImmunizationApi.get_imms_id", return_value=results):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(file_key, supplier, "covid19", None, {"NEW", "UPDATE", "DELETE"})

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("Success", content)
        mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_positive_string_provided(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"NEW", "UPDATE", "DELETE"}
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constants.file_content)
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
        with patch("batch_processing.ImmunizationApi.get_imms_id", return_value=results):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_request_positive_string)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(file_key, supplier, "covid19", None, permission_operations)

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("Success", content)
        mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_only_mandatory(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"NEW", "UPDATE", "DELETE"}

        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constants.file_content)
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
        with patch("batch_processing.ImmunizationApi.get_imms_id", return_value=results):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_request_only_mandatory)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(file_key, supplier, "covid19", None, permission_operations)

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("Success", content)
        mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_positive_string_not_provided(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"NEW", "UPDATE", "DELETE"}
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constants.file_content)
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
        with patch("batch_processing.ImmunizationApi.get_imms_id", return_value=results):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_request_positive_string_missing)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(file_key, supplier, "covid19", None, permission_operations)
        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("Success", content)
        mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_invalid(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"NEW", "UPDATE", "DELETE"}
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constants.file_content)
        with patch("batch_processing.convert_to_fhir_json", return_value=({}, False)):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(file_key, supplier, Constants.valid_vaccine_type[1], None, permission_operations)

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("fatal-error", content)
        mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_paramter_missing(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"NEW", "UPDATE", "DELETE"}
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constants.file_content)
        with patch("batch_processing.convert_to_fhir_json", return_value=({}, True)):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_request_params_missing)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(file_key, supplier, Constants.valid_vaccine_type[1], None, permission_operations)

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("fatal-error", content)
        mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_failed(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"NEW", "UPDATE", "DELETE"}

        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constants.file_content_id_missing)
        results = {"total": 0}, 400
        with patch("batch_processing.convert_to_fhir_json", return_value=({}, True)), patch(
            "batch_processing.ImmunizationApi.get_imms_id", return_value=results
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_update_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(file_key, supplier, "covid19", None, permission_operations)

        ack_filename = "processedFile/test-file_response.csv"
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response["Body"].read().decode("utf-8")
        self.assertIn("fatal-error", content)
        mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_successful(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test-file.csv"
        supplier = "test"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"NEW", "UPDATE", "DELETE"}
        csv_content = Constants.file_content
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
        vaccine_types = Constants.valid_vaccine_type
        for vaccine_type in vaccine_types:
            with patch("batch_processing.ImmunizationApi.get_imms_id", return_value=results):
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_update_request)
                mock_csv_dict_reader.return_value = mock_csv_reader_instance
                process_csv_to_fhir(
                    file_key,
                    supplier,
                    vaccine_type,
                    None,
                    permission_operations,
                )

            ack_filename = "processedFile/test-file_response.csv"
            response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
            content = response["Body"].read().decode("utf-8")
            self.assertIn("Success", content)
            mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_successful_permissions(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test_file.csv"
        supplier = "test"
        message_id = "test-idr"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"NEW", "UPDATE", "DELETE"}
        csv_content = Constants.file_content_operations
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
        vaccine_types = Constants.valid_vaccine_type
        for vaccine_type in vaccine_types:
            with patch("batch_processing.ImmunizationApi.get_imms_id", return_value=results):
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_update_request)
                mock_csv_dict_reader.return_value = mock_csv_reader_instance
                process_csv_to_fhir(file_key, supplier, vaccine_type, message_id, permission_operations)

            ack_filename = "processedFile/test_file_response.csv"
            response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
            content = response["Body"].read().decode("utf-8")
            self.assertIn("Success", content)
            mock_send_to_kinesis.assert_called()

    @mock_s3
    @mock_kinesis
    @patch("batch_processing.send_to_kinesis")
    @patch("csv.DictReader")
    def test_process_csv_to_fhir_incorrect_permissions(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client = boto3.client("s3", region_name="eu-west-2")
        bucket_name = "immunisation-batch-internal-dev-data-source"
        file_key = "test_file.csv"
        supplier = "test"
        message_id = "test-id"
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        permission_operations = {"DELETE"}
        csv_content = Constants.file_content
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
        vaccine_types = Constants.valid_vaccine_type
        for vaccine_type in vaccine_types:
            with patch("batch_processing.ImmunizationApi.get_imms_id", return_value=results):
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance = MagicMock()
                mock_csv_reader_instance.__iter__.return_value = iter(Constants.mock_update_request)
                mock_csv_dict_reader.return_value = mock_csv_reader_instance
                process_csv_to_fhir(file_key, supplier, vaccine_type, message_id, permission_operations)

            # Called once to send no permissions message to forwarder lambda
            ack_filename = "processedFile/test_file_response.csv"
            response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
            content = response["Body"].read().decode("utf-8")
            self.assertIn("No permissions for operation", content)
            mock_send_to_kinesis.assert_called()

    def test_process_csv_to_fhir_successful_Practitioner(self):
        request = Constants.request
        request["PERFORMING_PROFESSIONAL_FORENAME"] = ""
        request["PERFORMING_PROFESSIONAL_SURNAME"] = ""
        vaccine_types = Constants.valid_vaccine_type
        for vaccine_type in vaccine_types:
            json, valid = convert_to_fhir_json(request, vaccine_type)

        self.assertNotIn("Practitioner", [res["resourceType"] for res in json.get("contained", [])])
        self.assertNotIn(
            "reference",
            [
                performer.get("reference")
                for res in json.get("actor", [])
                if "performer" in res
                for performer in res.get("performer", [])
            ],
        )

    def test_process_csv_to_fhir_successful_qualitycode(self):
        request = Constants.request
        request["DOSE_UNIT_CODE"] = ""
        vaccine_types = Constants.valid_vaccine_type

        for vaccine_type in vaccine_types:
            json, valid = convert_to_fhir_json(request, vaccine_type)
            dose_quality = json.get("doseQuality", {})
            self.assertNotIn("system", dose_quality)

    def test_process_csv_to_fhir_successful_vaccine_code(self):
        request = Constants.request
        request["VACCINE_PRODUCT_CODE"] = ""
        request["VACCINE_PRODUCT_TERM"] = ""
        vaccine_types = Constants.valid_vaccine_type

        for vaccine_type in vaccine_types:
            json, valid = convert_to_fhir_json(request, vaccine_type)
            vaccine_code = json.get("vaccineCode", {})
            self.assertIn("NAVU", vaccine_code["coding"][0]["code"])
            self.assertIn("Not available", vaccine_code["coding"][0]["display"])

    def test_get_environment(self):
        with patch("batch_processing.os.getenv", return_value="internal-dev"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

        with patch("batch_processing.os.getenv", return_value="prod"):
            env = get_environment()
            self.assertEqual(env, "prod")

        with patch("batch_processing.os.getenv", return_value="unknown-env"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

    # TODO: ADD NEW PERMISSIONS LOGIC
    # @patch("batch_processing.get_supplier_permissions")
    # def test_no_permissions(self, mock_get_supplier_permissions):
    #     mock_get_supplier_permissions.return_value = [""]
    #     config_bucket_name = "test-bucket"
    #     supplier = "test-supplier"
    #     vaccine_type = "COVID19"

    #     result = validate_full_permissions(config_bucket_name, supplier, vaccine_type)

    #     self.assertFalse(result)

    @patch("batch_processing.get_permissions_config_json_from_s3")
    def test_get_supplier_permissions_success(self, mock_get_permissions_config_json_from_s3):
        # Mock S3 response
        mock_get_permissions_config_json_from_s3.return_value = Constants.test_permissions_config_file

        supplier = "SUPPLIER1"
        config_bucket_name = "test-config-bucket"

        permissions = get_supplier_permissions(supplier)

        self.assertEqual(permissions, ["COVID19_CREATE", "COVID19_DELETE", "COVID19_UPDATE"])

    @patch("batch_processing.get_permissions_config_json_from_s3")
    def test_get_supplier_permissions_no_permissions(self, mock_get_permissions_config_json_from_s3):
        mock_get_permissions_config_json_from_s3.return_value = Constants.test_permissions_config_file

        supplier = "SUPPLIER4"
        config_bucket_name = "test-config-bucket"

        permissions = get_supplier_permissions(supplier)

        self.assertEqual(permissions, [""])

    # TODO: REPLACE WITH NEW PERMISSIONS LOGIC
    # @patch("batch_processing.get_supplier_permissions")
    # def test_validate_full_permissions_valid(self, mock_get_supplier_permissions):
    #     mock_get_supplier_permissions.return_value = ["FLU_FULL", "MMR_CREATE"]

    #     supplier = "supplier1"
    #     config_bucket_name = "test-config-bucket"
    #     vaccine_type = "FLU"

    #     result = validate_full_permissions(config_bucket_name, supplier, vaccine_type)

    #     self.assertTrue(result)

    # TODO: REPLACE WITH NEW PERMISSIONS LOGIC
    #  @patch("batch_processing.get_supplier_permissions")
    # def test_validate_full_permissions_invalid(self, mock_get_supplier_permissions):
    #     mock_get_supplier_permissions.return_value = ["COVID19_CREATE"]

    #     supplier = "supplier1"
    #     config_bucket_name = "test-config-bucket"
    #     vaccine_type = "COVID19"

    #     result = validate_full_permissions(config_bucket_name, supplier, vaccine_type)

    #     self.assertFalse(result)

    @patch("batch_processing.get_supplier_permissions")
    def test_get_action_flag_permissions_success(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["MMR_FULL", "FLU_CREATE", "FLU_UPDATE"]

        supplier = "supplier1"
        vaccine_type = "FLU"

        operations = get_action_flag_permissions(supplier, vaccine_type)

        self.assertEqual(operations, {"UPDATE", "NEW"})

    @patch("batch_processing.get_supplier_permissions")
    def test_get_action_flag_permissions_one_permission(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["MMR_UPDATE"]

        supplier = "supplier1"
        vaccine_type = "MMR"

        operations = get_action_flag_permissions(supplier, vaccine_type)

        self.assertEqual(operations, {"UPDATE"})


if __name__ == "__main__":
    unittest.main()
