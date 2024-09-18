import unittest
import os
import io
# import json
from unittest.mock import patch, MagicMock
# import boto3
from moto import mock_sqs
from router_lambda_function import (
    identify_supplier,
    identify_vaccine_type,
    identify_timestamp,
    initial_file_validation,
    send_to_supplier_queue,
    create_ack_file,
    extract_ods_code,
    validate_vaccine_type_permissions,
    validate_action_flag_permissions,
)
from src.constants import Constant


class TestRouterLambdaFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        cls.ods_code = "YGM41"

    def test_identify_supplier(self):
        """tests supplier is correctly matched"""
        supplier = identify_supplier(self.ods_code)
        self.assertEqual(supplier, "EMIS")

    def test_extract_ods_code(self):
        """tests supplier ODS code is extracted"""
        ods_code = extract_ods_code(self.file_key)
        self.assertEqual(ods_code, "YGM41")

    def test_identify_vaccine_type(self):
        """tests vaccine type is extracted"""
        vaccine_type = identify_vaccine_type(self.file_key)
        self.assertEqual(vaccine_type, "Flu")

    def test_identify_timestamp(self):
        """tests timestamp is extracted"""
        timestamp = identify_timestamp(self.file_key)
        self.assertEqual(timestamp, "20240708T12130100")

    @patch("router_lambda_function.validate_csv_column_count")
    @patch("router_lambda_function.validate_action_flag_permissions")
    @patch("router_lambda_function.get_supplier_permissions")
    def test_valid_file(
        self,
        mock_get_permissions,
        mock_validate_action_flag_permissions,
        mock_validate_csv,
    ):
        mock_validate_csv.return_value = (True, [])
        mock_get_permissions.return_value = ["FLU_CREATE", "FLU_UPDATE"]
        mock_validate_action_flag_permissions.return_value = True
        file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name)
        print(f"VALID: {valid}")
        self.assertTrue(valid)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_extension(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.txt"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_file_structure(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_vaccine_type(self, mock_validate_csv):
        file_key = "Invalid_Vaccinations_v5_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_version(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v3_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_ods_code(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_INVALID_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_timestamp(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41_20240708Ta99999999.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_column_count(self, mock_validate_csv):
        mock_validate_csv.return_value = (False, True)
        file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)

    @patch("router_lambda_function.sqs_client")
    def test_supplier_queue_1(self, mock_sqs_client):
        """tests if supplier queue is called"""
        mock_send_message = mock_sqs_client.send_message
        supplier = "EMIS"
        message_body = {
            "vaccine_type": "Flu",
            "supplier": supplier,
            "timestamp": "20240708T12130100",
            "filename": "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
        }
        send_to_supplier_queue(supplier, message_body)
        mock_send_message.assert_called_once()

    @patch("router_lambda_function.s3_client")
    def test_create_ack_file(self, mock_s3_client):
        """tests whether ack file is created"""
        ack_bucket_name = "immunisation-batch-internal-dev-data-destination"
        validation_passed = True
        created_at_formatted = "20240725T12510700"
        create_ack_file(
            "1",
            self.file_key,
            ack_bucket_name,
            validation_passed,
            True,
            created_at_formatted,
        )
        mock_s3_client.upload_fileobj.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "internal-dev",
            "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
            "LOCAL_ACCOUNT_ID": "123456789012",
            "PROD_ACCOUNT_ID": "3456789109",
        },
    )
    @mock_sqs
    @patch("router_lambda_function.os.getenv")
    def test_send_to_supplier_queue_queue_not_exist(self, mock_getenv):
        """
        Test send_to_supplier_queue function when the queue does not exist.
        """
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
            "LOCAL_ACCOUNT_ID": "123456789012",
            "PROD_ACCOUNT_ID": "3456789109",
        }.get(key, default)

        supplier = "STAR"
        message_body = {
            "vaccine_type": "Flu",
            "supplier": supplier,
            "timestamp": "20240708T12130100",
            "filename": "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
        }

        success = send_to_supplier_queue(supplier, message_body)
        self.assertFalse(success)

    @patch("router_lambda_function.get_supplier_permissions")
    def test_validate_permissions(self, mock_get_permissions):
        """Test validate vaccine type permissions"""
        mock_get_permissions.return_value = ["FLU_DELETE", "FLU_CREATE", "COVID19_FULL"]

        result = validate_vaccine_type_permissions("test-bucket", "supplierA", "FLU")
        self.assertTrue(result)

        result = validate_vaccine_type_permissions("test-bucket", "supplierA", "MMR")
        self.assertFalse(result)

        result = validate_vaccine_type_permissions(
            "test-bucket", "supplierA", "COVID19"
        )
        self.assertTrue(result)


class TestValidateActionFlagPermissions(unittest.TestCase):
    """Test validate action flag permissions"""

    @patch("router_lambda_function.s3_client")
    @patch("router_lambda_function.get_supplier_permissions")
    # @patch("csv.DictReader")
    def test_validate_action_flag_permissions(
        self, mock_get_supplier_permissions, mock_s3_client
    ):
        # Sample CSV data
        csv_data = Constant.file_content_operations

        # Mock S3 get_object
        mock_s3_client.get_object.return_value = {
            "Body": io.BytesIO(csv_data.encode("utf-8"))
        }

        # Mock get_supplier_permissions
        mock_get_supplier_permissions.return_value = [
            "COVID19_DELETE",
            "MMR_UPDATE",
            "FLU_CREATE",
        ]

        mock_csv_reader_instance = MagicMock()
        mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
        # mock_csv_dict_reader.return_value = mock_csv_reader_instance
        # Define test parameters
        bucket_name = "test-bucket"
        file_key = "Flu_Vaccinations_v5_YYY78_20240708T12130100.csv"
        supplier = "supplier_123"
        vaccine_type = "FLU"
        config_bucket_name = "config-bucket"

        # Call the function
        result = validate_action_flag_permissions(
            bucket_name, file_key, supplier, vaccine_type, config_bucket_name
        )
        print(f"TEST_RESULT{result}")
        # Check the result
        self.assertTrue(result)

    @patch("router_lambda_function.s3_client")
    @patch("router_lambda_function.get_supplier_permissions")
    def test_validate_action_flag_permissions_with_one_permissions(
        self, mock_get_supplier_permissions, mock_s3_client
    ):
        # Sample CSV data
        csv_data = Constant.file_content_operations

        # Mock S3 get_object
        mock_s3_client.get_object.return_value = {
            "Body": io.BytesIO(csv_data.encode("utf-8"))
        }

        # Mock get_supplier_permissions
        mock_get_supplier_permissions.return_value = ["FLU_DELETE"]

        # Define test parameters
        bucket_name = "test-bucket"
        file_key = "Flu_Vaccinations_v5_YYY78_20240708T12130100.csv"
        supplier = "supplier_123"
        vaccine_type = "FLU"
        config_bucket_name = "config_bucket"

        # Call the function
        result = validate_action_flag_permissions(
            bucket_name, file_key, supplier, vaccine_type, config_bucket_name
        )

        # Check the result
        self.assertTrue(result)

    @patch("router_lambda_function.s3_client")
    @patch("router_lambda_function.get_supplier_permissions")
    def test_validate_action_flag_permissions_with_full_permissions(
        self, mock_get_supplier_permissions, mock_s3_client
    ):
        # Sample CSV data
        csv_data = Constant.file_content_operations

        # Mock S3 get_object
        mock_s3_client.get_object.return_value = {
            "Body": io.BytesIO(csv_data.encode("utf-8"))
        }

        # Mock get_supplier_permissions
        mock_get_supplier_permissions.return_value = ["COVID19_FULL"]

        # Define test parameters
        bucket_name = "test-bucket"
        file_key = "COVID19_Vaccinations_v5_YYY78_20240708T12130100.csv"
        supplier = "supplier_test"
        vaccine_type = "COVID19"
        config_bucket_name = "config-bucket"

        # Call the function
        result = validate_action_flag_permissions(
            bucket_name, file_key, supplier, vaccine_type, config_bucket_name
        )

        # Check the result
        self.assertTrue(result)

    @patch("router_lambda_function.s3_client")
    @patch("router_lambda_function.get_supplier_permissions")
    def test_validate_action_flag_permissions_with_no_permissions(
        self, mock_get_supplier_permissions, mock_s3_client
    ):
        # Sample CSV data
        csv_data = Constant.file_content_operations

        # Mock S3 get_object
        mock_s3_client.get_object.return_value = {
            "Body": io.BytesIO(csv_data.encode("utf-8"))
        }

        # Mock get_supplier_permissions
        mock_get_supplier_permissions.return_value = ["COVID19_UPDATE"]

        # Define test parameters
        bucket_name = "test-bucket"
        file_key = "COVID19_Vaccinations_v5_YYY78_20240708T12130100.csv"
        supplier = "supplier_test"
        vaccine_type = "COVID19"
        config_bucket_name = "config-bucket"

        # Call the function
        result = validate_action_flag_permissions(
            bucket_name, file_key, supplier, vaccine_type, config_bucket_name
        )

        # Check the result
        self.assertFalse(result)
