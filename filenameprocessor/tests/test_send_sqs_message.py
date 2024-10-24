"""Tests for send_sqs_message functions"""

from unittest import TestCase
from unittest.mock import patch, MagicMock
from json import loads as json_loads
from uuid import uuid4
from moto import mock_sqs
from boto3 import client as boto3_client
import os
import sys
maindir = os.path.dirname(__file__)
srcdir = '../src'
sys.path.insert(0, os.path.abspath(os.path.join(maindir, srcdir)))
from send_sqs_message import send_to_supplier_queue, make_message_body_for_sqs, make_and_send_sqs_message
from utils_for_tests.values_for_tests import MOCK_ENVIRONMENT_DICT, SQS_ATTRIBUTES


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestSendSQSMessage(TestCase):
    """Tests for send_sqs_message functions"""

    @mock_sqs
    def test_send_to_supplier_queue_success(self):
        """Test send_to_supplier_queue function for a successful message send"""
        mock_sqs_client = boto3_client("sqs", region_name="eu-west-2")

        # Set up the queue
        supplier = "PINNACLE"
        message_body = {"supplier": supplier}
        # The short form of the supplier name is used for the queue name
        queue_name = "imms-batch-internal-dev-metadata-queue.fifo"
        queue_url = mock_sqs_client.create_queue(QueueName=queue_name, Attributes=SQS_ATTRIBUTES)["QueueUrl"]

        # Call the send_to_supplier_queue function
        self.assertTrue(send_to_supplier_queue(message_body))

        # Assert that correct message has reached the queue
        messages = mock_sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        self.assertEqual(json_loads(messages["Messages"][0]["Body"]), {"supplier": "PINNACLE"})

    @mock_sqs
    def test_send_to_supplier_queue_failure_due_to_queue_does_not_exist(self):
        """Test send_to_supplier_queue function for a failed message send due to queue not existing"""
        supplier = "PINNACLE"
        message_body = {"supplier": supplier}
        self.assertFalse(send_to_supplier_queue(message_body))

    @mock_sqs
    def test_send_to_supplier_queue_failure_due_to_absent_supplier(self):
        """Test send_to_supplier_queue function for a failed message send"""
        mock_sqs_client = boto3_client("sqs", region_name="eu-west-2")
        mock_sqs_client.send_message = MagicMock()

        # Set up the queue
        supplier = ""
        message_body = {"supplier": supplier}
        # If attempt is made to send message then the queue name would be missing the supplier
        queue_name = "imms-batch-internal-dev--metadata-queue.fifo"
        _ = mock_sqs_client.create_queue(QueueName=queue_name, Attributes=SQS_ATTRIBUTES)["QueueUrl"]

        # Call the send_to_supplier_queue function
        with patch("send_sqs_message.sqs_client", mock_sqs_client):
            self.assertFalse(send_to_supplier_queue(message_body))
            mock_sqs_client.send_message.assert_not_called()

    def test_make_message_body_for_sqs(self):
        """Test that make_message_body_for_sqs returns a correctly formatted message body"""
        file_key = "Flu_Vaccinations_v5_0DF_20200101T12345600.csv"
        message_id = str(uuid4())
        permission = "FLU_FULL"
        expected_output = {
            "message_id": message_id,
            "vaccine_type": "FLU",
            "supplier": "NIMS",
            "timestamp": "20200101T12345600",
            "filename": file_key,
            "permission": permission
        }

        self.assertEqual(make_message_body_for_sqs(file_key, message_id, permission), expected_output)

    @mock_sqs
    def test_make_and_send_sqs_message_success(self):
        """Test make_and_send_sqs_message function for a successful message send"""
        mock_sqs_client = boto3_client("sqs", region_name="eu-west-2")

        # Set up message details, using the ODS code for MEDICAL_DIRECTOR in the file_key
        # The short form of the supplier name is used for the queue name
        queue_name = "imms-batch-internal-dev-metadata-queue.fifo"
        file_key = "Covid19_Vaccinations_v5_YGMYH_20200101T12345600.csv"
        message_id = str(uuid4())
        permission = "FLU_FULL"
        expected_message_body = {
            "message_id": message_id,
            "vaccine_type": "COVID19",
            "supplier": "MEDICAL_DIRECTOR",
            "timestamp": "20200101T12345600",
            "filename": file_key,
            "permission": permission
        }

        # Create a mock SQS queue
        queue_url = mock_sqs_client.create_queue(QueueName=queue_name, Attributes=SQS_ATTRIBUTES)["QueueUrl"]

        # Call the send_to_supplier_queue function
        self.assertTrue(make_and_send_sqs_message(file_key=file_key, message_id=message_id, permission=permission))

        # Assert that correct message has reached the queue
        messages = mock_sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        self.assertEqual(json_loads(messages["Messages"][0]["Body"]), expected_message_body)

    @mock_sqs
    def test_make_and_send_sqs_message_failure(self):
        """Test make_and_send_sqs_message function for a failure due to queue not existing"""
        file_key = "Covid19_Vaccinations_v5_YGMYH_20200101T12345600.csv"
        message_id = str(uuid4())
        permission = "FLU_FULL"
        self.assertFalse(make_and_send_sqs_message(file_key=file_key, message_id=message_id, permission=permission))
