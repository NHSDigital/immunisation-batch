import unittest
import os
import json
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_sqs
from router_lambda_function import (
    identify_supplier,
    identify_vaccine_type,
    identify_timestamp,
    initial_file_validation,
    send_to_supplier_queue,
    create_ack_file,
    extract_ods_code,
    lambda_handler,
)


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
    def test_valid_file(self, mock_validate_csv):
        mock_validate_csv.return_value = (True, [])
        file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertTrue(valid)
        self.assertFalse(errors)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_extension(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.txt"
        bucket_name = "test-bucket"

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_file_structure(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41.csv"
        bucket_name = "test-bucket"

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_vaccine_type(self, mock_validate_csv):
        file_key = "Invalid_Vaccinations_v5_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_version(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v3_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_ods_code(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_INVALID_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_timestamp(self, mock_validate_csv):
        file_key = "Flu_Vaccinations_v5_YGM41_20240708Ta99999999.csv"
        bucket_name = "test-bucket"

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch("router_lambda_function.validate_csv_column_count")
    def test_invalid_column_count(self, mock_validate_csv):
        mock_validate_csv.return_value = (False, True)
        file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        bucket_name = "test-bucket"

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertEqual(errors, True)

    @patch("router_lambda_function.sqs_client")
    def test_supplier_queue_1(self, mock_sqs_client):
        """tests if supplier queue is called"""
        mock_send_message = mock_sqs_client.send_message
        supplier = "EMIS"
        message_body = {
            "vaccine_type": "Flu",
            "supplier": supplier,
            "timestamp": "20240708T12130100",
        }
        send_to_supplier_queue(supplier, message_body)
        mock_send_message.assert_called_once()

    @patch("router_lambda_function.s3_client")
    def test_create_ack_file(self, mock_s3_client):
        """tests whether ack file is created"""
        ack_bucket_name = "immunisation-batch-internal-dev-batch-data-destination"
        validation_passed = True
        created_at_formatted = "20240725T12510700"
        create_ack_file(
            self.file_key, ack_bucket_name, validation_passed, created_at_formatted
        )
        mock_s3_client.upload_fileobj.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "internal-dev",
            "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
            "LOCAL_ACCOUNT_ID": "123456789012",
        },
    )
    @patch("router_lambda_function.sqs_client")  # Mock the SQS client
    def test_send_to_supplier_queue(self, mock_sqs_client):
        """tests SQS queue is sent a message for valid files"""
        # Define the mock SQS queue URL
        mock_queue_url = "https://sqs.eu-west-2.amazonaws.com/123456789012/imms-batch-internal-dev-EMIS-metadata-queue.fifo"
        mock_sqs_client.get_queue_url = MagicMock(
            return_value={"QueueUrl": mock_queue_url}
        )

        mock_send_message = MagicMock()
        mock_sqs_client.send_message = mock_send_message

        supplier = "EMIS"
        message_body = {
            "vaccine_type": "flu",
            "supplier": supplier,
            "timestamp": "20240709T121304",
        }

        # Call the send_to_supplier_queue function
        send_to_supplier_queue(supplier, message_body)

        # Assert that send_message was called once
        mock_send_message.assert_called_once()

        args, kwargs = mock_send_message.call_args

        self.assertEqual(kwargs["QueueUrl"], mock_queue_url)

        self.assertIn("MessageBody", kwargs)
        actual_message_body = json.loads(kwargs["MessageBody"])
        self.assertEqual(actual_message_body["vaccine_type"], "flu")
        self.assertEqual(actual_message_body["supplier"], "EMIS")
        self.assertEqual(actual_message_body["timestamp"], "20240709T121304")

    @mock_sqs
    @patch("router_lambda_function.os.getenv")
    @patch("router_lambda_function.uuid.uuid4", return_value="12345")
    def test_send_to_supplier_queue_success(self, mock_uuid, mock_getenv):
        """
        Test send_to_supplier_queue function for a successful message send.

        """
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
            "LOCAL_ACCOUNT_ID": "123456789012",
        }.get(key, default)

        # Create a mock SQS queue
        sqs = boto3.client("sqs", region_name="eu-west-2")
        queue_url = sqs.create_queue(
            QueueName="imms-batch-internal-dev-EMIS-metadata-queue.fifo",
            Attributes={"FifoQueue": "true"},
        )["QueueUrl"]

        supplier = "EMIS"
        message_body = {
            "vaccine_type": "Flu",
            "supplier": supplier,
            "timestamp": "20240708T12130100",
        }

        # Call the send_to_supplier_queue function
        success = send_to_supplier_queue(supplier, message_body)

        self.assertTrue(success)

        messages = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        self.assertIn("Messages", messages)
        message_body_received = json.loads(messages["Messages"][0]["Body"])
        self.assertEqual(message_body_received["vaccine_type"], "Flu")
        self.assertEqual(message_body_received["supplier"], supplier)
        self.assertEqual(message_body_received["timestamp"], "20240708T12130100")

    @mock_sqs
    @patch("router_lambda_function.os.getenv")
    @patch("router_lambda_function.uuid.uuid4", return_value="12345")
    def test_send_to_supplier_queue_queue_not_exist(self, mock_uuid, mock_getenv):
        """
        Test send_to_supplier_queue function when the queue does not exist.
        """
        # Mock environment variables
        mock_getenv.side_effect = lambda key, default=None: {
            "SHORT_QUEUE_PREFIX": "imms-batch-internal-dev",
            "LOCAL_ACCOUNT_ID": "123456789012",
        }.get(key, default)

        supplier = "STAR"
        message_body = {
            "vaccine_type": "Flu",
            "supplier": supplier,
            "timestamp": "20240708T12130100",
        }

        success = send_to_supplier_queue(supplier, message_body)
        self.assertFalse(success)
