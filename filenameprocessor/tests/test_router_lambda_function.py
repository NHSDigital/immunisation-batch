import unittest
import os
import io
import json
import csv
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_sqs
from router_lambda_function import make_and_upload_ack_file
from send_to_supplier_queue import send_to_supplier_queue
from initial_file_validation import (
    initial_file_validation,
    validate_vaccine_type_permissions,
    validate_action_flag_permissions,
)
from utils_for_filenameprocessor import identify_supplier
from src.constants import Constants


def convert_csv_to_string(filename):
    file_path = f"{os.path.dirname(os.path.abspath(__file__))}/{filename}"
    with open(file_path, mode="r", encoding="utf-8") as file:
        return "".join(file.readlines())


def convert_csv_to_reader(filename):
    file_path = f"{os.path.dirname(os.path.abspath(__file__))}/{filename}"
    with open(file_path, mode="r", encoding="utf-8") as file:
        data = file.read()
    return csv.reader(io.StringIO(data), delimiter="|")


def convert_string_to_dict_reader(data_string: str):
    return csv.DictReader(io.StringIO(data_string), delimiter="|")


class TestRouterLambdaFunctions(unittest.TestCase):
    def setUp(self):
        self.file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        self.bucket_name = "test-bucket"
        self.ods_code = "YGM41"
        self.mock_s3_client = MagicMock()
        self.mock_sqs_client = MagicMock()

    def test_identify_supplier(self):
        """tests supplier is correctly matched"""
        self.assertEqual(identify_supplier(self.ods_code), "EMIS")
        self.assertEqual(identify_supplier("NOT_A_VALID_ODS_CODE"), None)

    # TODO: Test extract_file_key_elements function

    def test_valid_file(self):
        valid_csv_content_dict_reader = convert_string_to_dict_reader(Constants.valid_file_content)

        with (
            patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_CREATE", "FLU_UPDATE"]),
            patch("initial_file_validation.get_csv_content_dict_reader", return_value=valid_csv_content_dict_reader),
        ):
            self.assertTrue(initial_file_validation(self.file_key, self.bucket_name, self.mock_s3_client))

    @patch("initial_file_validation.validate_content_headers")
    def test_invalid_extension(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.txt"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name, self.mock_s3_client)
        self.assertFalse(valid)

    @patch("initial_file_validation.validate_content_headers")
    def test_invalid_file_structure(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name, self.mock_s3_client)
        self.assertFalse(valid)

    @patch("initial_file_validation.validate_content_headers")
    def test_invalid_vaccine_type(self, mock_validate_csv):
        file_key = "Invalid_Vaccinations_v5_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name, self.mock_s3_client)
        self.assertFalse(valid)

    @patch("initial_file_validation.validate_content_headers")
    def test_invalid_version(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v3_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name, self.mock_s3_client)
        self.assertFalse(valid)

    @patch("initial_file_validation.validate_content_headers")
    def test_invalid_ods_code(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_INVALID_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name, self.mock_s3_client)
        self.assertFalse(valid)

    @patch("initial_file_validation.validate_content_headers")
    def test_invalid_timestamp(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41_20240708Ta99999999.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name, self.mock_s3_client)
        self.assertFalse(valid)

    @patch("initial_file_validation.get_csv_content_dict_reader")
    @patch("initial_file_validation.validate_content_headers")
    def test_invalid_column_count(self, mock_validate_content_headers, mock_get_csv_content_dict_reader):
        mock_get_csv_content_dict_reader.return_value = convert_string_to_dict_reader(Constants.valid_file_content)
        mock_validate_content_headers.return_value = False
        file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid = initial_file_validation(file_key, bucket_name, self.mock_s3_client)
        self.assertFalse(valid)

    # @patch("router_lambda_function.sqs_client")
    def test_supplier_queue_1(self):
        """tests if supplier queue is called"""
        mock_send_message = self.mock_sqs_client.send_message
        supplier = "EMIS"
        message_body = {
            "vaccine_type": "Flu",
            "supplier": supplier,
            "timestamp": "20240708T12130100",
            "filename": "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
        }
        send_to_supplier_queue(message_body, self.mock_sqs_client)
        mock_send_message.assert_called_once()

    def test_make_and_upload_ack_file(self):
        """tests whether ack file is created"""
        validation_passed = True
        created_at_formatted = "20240725T12510700"
        make_and_upload_ack_file("1", self.file_key, validation_passed, True, created_at_formatted, self.mock_s3_client)
        self.mock_s3_client.upload_fileobj.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "internal-dev",
            "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
            "LOCAL_ACCOUNT_ID": "123456789012",
            "PROD_ACCOUNT_ID": "3456789109",
        },
    )
    def test_send_to_supplier_queue(self):
        """tests SQS queue is sent a message for valid files"""
        # Define the mock SQS queue URL
        mock_url = "https://sqs.eu-west-2.amazonaws.com/123456789012/imms-batch-internal-dev-EMIS-metadata-queue.fifo"
        self.mock_sqs_client.get_queue_url = MagicMock(return_value={"QueueUrl": mock_url})

        mock_send_message = MagicMock()
        self.mock_sqs_client.send_message = mock_send_message

        supplier = "EMIS"
        message_body = {
            "vaccine_type": "flu",
            "supplier": supplier,
            "timestamp": "20240709T121304",
            "filename": "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
        }

        # Call the send_to_supplier_queue function
        send_to_supplier_queue(message_body, self.mock_sqs_client)

        # Assert that send_message was called once
        mock_send_message.assert_called_once()

        args, kwargs = mock_send_message.call_args

        self.assertEqual(kwargs["QueueUrl"], mock_url)

        self.assertIn("MessageBody", kwargs)
        actual_message_body = json.loads(kwargs["MessageBody"])
        self.assertEqual(actual_message_body["vaccine_type"], "flu")
        self.assertEqual(actual_message_body["supplier"], "EMIS")
        self.assertEqual(actual_message_body["timestamp"], "20240709T121304")
        self.assertEqual(
            actual_message_body["filename"],
            "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
        )

    @mock_sqs
    @patch("utils_for_filenameprocessor.os.getenv")
    def test_send_to_supplier_queue_success(self, mock_getenv):
        """
        Test send_to_supplier_queue function for a successful message send.

        """
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
            "LOCAL_ACCOUNT_ID": "123456789012",
            "PROD_ACCOUNT_ID": "3456789109",
        }.get(key, default)

        # Create a mock SQS queue
        sqs = boto3.client("sqs", region_name="eu-west-2")
        queue_url = sqs.create_queue(
            QueueName="imms-batch-internal-dev-EMIS-metadata-queue.fifo",
            Attributes={"FifoQueue": "true", "ContentBasedDeduplication": "true"},
        )["QueueUrl"]

        supplier = "EMIS"
        message_body = {
            "vaccine_type": "Flu",
            "supplier": supplier,
            "timestamp": "20240708T12130100",
            "filename": "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
        }

        # Call the send_to_supplier_queue function
        success = send_to_supplier_queue(message_body, sqs)

        self.assertTrue(success)

        messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        self.assertIn("Messages", messages)
        message_body_received = json.loads(messages["Messages"][0]["Body"])
        self.assertEqual(message_body_received["vaccine_type"], "Flu")
        self.assertEqual(message_body_received["supplier"], supplier)
        self.assertEqual(message_body_received["timestamp"], "20240708T12130100")
        self.assertEqual(
            message_body_received["filename"],
            "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
        )

    @mock_sqs
    @patch("utils_for_filenameprocessor.os.getenv")
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

        # Create a mock SQS queue
        mock_sqs = boto3.client("sqs", region_name="eu-west-2")

        supplier = "STAR"
        message_body = {
            "vaccine_type": "Flu",
            "supplier": supplier,
            "timestamp": "20240708T12130100",
            "filename": "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
        }

        # Call the send_to_supplier_queue function
        success = send_to_supplier_queue(message_body, mock_sqs)

        self.assertFalse(success)

    @patch("initial_file_validation.get_supplier_permissions")
    def test_validate_permissions(self, mock_get_permissions):
        """Test validate vaccine type permissions"""
        mock_get_permissions.return_value = ["FLU_DELETE", "FLU_CREATE", "COVID19_FULL"]

        result = validate_vaccine_type_permissions("supplierA", "FLU")
        self.assertTrue(result)

        result = validate_vaccine_type_permissions("supplierA", "MMR")
        self.assertFalse(result)

        result = validate_vaccine_type_permissions("supplierA", "COVID19")
        self.assertTrue(result)


class TestValidateActionFlagPermissions(unittest.TestCase):
    """Test validate action flag permissions"""

    def test_validate_action_flag_permissions(self):
        # Define test parameters
        allowed_permissions = ["COVID19_DELETE", "MMR_UPDATE", "FLU_CREATE"]
        supplier = "supplier_123"
        vaccine_type = "FLU"

        csv_content_dict_reader = convert_string_to_dict_reader(Constants.file_content_with_new_and_delete_action_flags)

        with patch("initial_file_validation.get_supplier_permissions", return_value=allowed_permissions):
            # Call the function
            result = validate_action_flag_permissions(csv_content_dict_reader, supplier, vaccine_type)

        # Check the result
        self.assertTrue(result)

    @patch("initial_file_validation.get_supplier_permissions")
    def test_validate_action_flag_permissions_with_one_permissions(self, mock_get_supplier_permissions):
        # Mock get_supplier_permissions
        mock_get_supplier_permissions.return_value = ["FLU_DELETE"]

        # Define test parameters
        supplier = "supplier_123"
        vaccine_type = "FLU"

        csv_content_dict_reader = convert_string_to_dict_reader(Constants.file_content_with_new_and_delete_action_flags)

        # Call the function
        result = validate_action_flag_permissions(csv_content_dict_reader, supplier, vaccine_type)

        # Check the result
        self.assertTrue(result)

    @patch("initial_file_validation.get_supplier_permissions")
    def test_validate_action_flag_permissions_with_full_permissions(self, mock_get_supplier_permissions):

        # Mock get_supplier_permissions
        mock_get_supplier_permissions.return_value = ["COVID19_FULL"]

        # Define test parameters
        supplier = "supplier_test"
        vaccine_type = "COVID19"

        csv_content_dict_reader = convert_string_to_dict_reader(Constants.file_content_with_new_and_delete_action_flags)

        # Call the function
        result = validate_action_flag_permissions(csv_content_dict_reader, supplier, vaccine_type)

        # Check the result
        self.assertTrue(result)

    @patch("initial_file_validation.get_supplier_permissions")
    def test_validate_action_flag_permissions_with_no_permissions(self, mock_get_supplier_permissions):

        # Mock get_supplier_permissions
        mock_get_supplier_permissions.return_value = ["COVID19_UPDATE"]

        # Define test parameters
        supplier = "supplier_test"
        vaccine_type = "COVID19"

        csv_content_dict_reader = convert_string_to_dict_reader(Constants.file_content_with_new_and_delete_action_flags)

        # Call the function
        result = validate_action_flag_permissions(csv_content_dict_reader, supplier, vaccine_type)

        # Check the result
        self.assertFalse(result)
