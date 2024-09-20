import unittest
import os
import io
import json
import csv
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_sqs, mock_s3
from router_lambda_function import make_and_upload_ack_file
from send_to_supplier_queue import send_to_supplier_queues
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
        send_to_supplier_queues(message_body, self.mock_sqs_client)
        mock_send_message.assert_called_once()

    def test_make_and_upload_ack_file(self):
        """tests whether ack file is created"""
        validation_passed = True
        created_at_formatted = "20240725T12510700"
        s3_client = MagicMock()
        with patch("create_ack_file.s3_client", s3_client):
            make_and_upload_ack_file("1", self.file_key, validation_passed, True, created_at_formatted)
        s3_client.upload_fileobj.assert_called_once()

    @mock_sqs
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
        send_to_supplier_queues(message_body, self.mock_sqs_client)

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
        success = send_to_supplier_queues(message_body, sqs)

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
        success = send_to_supplier_queues(message_body, mock_sqs)

        self.assertFalse(success)
