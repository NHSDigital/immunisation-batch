"""e2e tests for lambda_handler, including specific tests for action flag permissions"""

from unittest.mock import patch
import unittest
import json
from typing import Optional
import boto3
from moto import mock_s3, mock_sqs
from src.constants import Constants
from router_lambda_function import lambda_handler


class TestLambdaHandler(unittest.TestCase):
    """
    Tests for lambda_handler.
    NOTE: All helper functions default to use valid file content with 'Flu_Vaccinations_v5_YGM41_20240708T12130100.csv'
    as the test_file_key and'ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_response.csv' as the ack_file_key
    """

    def setUp(self):
        self.source_bucket_name = "immunisation-batch-internal-dev-data-source"
        self.destination_bucket_name = "immunisation-batch-internal-dev-data-destination"
        self.test_file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        self.ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_response.csv"

    def set_up_s3_buckets_and_upload_file(self, test_file_key: Optional[str] = None, test_file_content: str = None):
        """
        Sets up the S3 client, source and destination buckets and uploads the test file to the source bucket.
        Returns the S3 client
        """
        # Use the default test_file_key and test_file_content if these aren't provided as args
        test_file_key = test_file_key or self.test_file_key
        test_file_content = test_file_content or Constants.valid_file_content

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=self.source_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )
        s3_client.create_bucket(
            Bucket=self.destination_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        self.assertIn(self.source_bucket_name, buckets, f"Bucket {self.source_bucket_name} not found")
        self.assertIn(self.destination_bucket_name, buckets, f"Bucket {self.destination_bucket_name} not found")

        # Upload a test file
        s3_client.put_object(Bucket=self.source_bucket_name, Key=test_file_key, Body=test_file_content)

        return s3_client

    def make_event(self, test_file_key: Optional[str] = None):
        """
        Makes an event with s3 bucket name set to 'immunisation-batch-internal-dev-data-source'
        and s3 object key set to the test file key
        """
        return {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": self.source_bucket_name},
                        "object": {"key": (test_file_key or self.test_file_key)},
                    }
                }
            ]
        }

    def assert_ack_file_in_destination_s3_bucket(self, s3_client, ack_file_key: Optional[str] = None):
        """Assert that the ack file is in the destination S3 bucket"""
        ack_file_key = ack_file_key or self.ack_file_key  # Use the default ack_file_key if this isn't given as an arg
        ack_files = s3_client.list_objects_v2(Bucket=self.destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    def test_lambda_handler_full_permissions(self):
        """Tests lambda function end to end"""
        # Set up S3
        s3_client = self.set_up_s3_buckets_and_upload_file()

        # Set up SQS
        sqs_client = boto3.client("sqs", region_name="eu-west-2")
        queue_name = "imms-batch-internal-dev-EMIS-metadata-queue.fifo"
        attributes = {"FIFOQueue": "true", "ContentBasedDeduplication": "true"}
        queue_url = sqs_client.create_queue(QueueName=queue_name, Attributes=attributes)["QueueUrl"]

        # Mock get_supplier_permissions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]):
            # Call the lambda_handler function
            response = lambda_handler(self.make_event(), None)

        # Assertions
        self.assertEqual(response["statusCode"], 200)
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

        # Check if the message was sent to the SQS queue
        messages = sqs_client.receive_message(QueueUrl=queue_url, WaitTimeSeconds=1, MaxNumberOfMessages=1)
        self.assertIn("Messages", messages)
        received_message = json.loads(messages["Messages"][0]["Body"])

        # Validate message content
        self.assertEqual(received_message["vaccine_type"], "FLU")
        self.assertEqual(received_message["supplier"], "EMIS")
        self.assertEqual(received_message["timestamp"], "20240708T12130100")
        self.assertEqual(received_message["filename"], "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv")

    @mock_s3
    def test_lambda_invalid_csv_header(self):
        """tests SQS queue is not called when CSV headers are invalid due to misspelled header"""
        s3_client = self.set_up_s3_buckets_and_upload_file(
            test_file_content=Constants.valid_file_content.replace("PERSON_DOB", "PERON_DOB"),
        )

        # Mock the get_supplier_permissions functions and send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:

            # Call the lambda_handler function
            lambda_handler(event=self.make_event(), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

        # Validate the content of the ack file to ensure it reports an error due to invalid headers
        ack_file_obj = s3_client.get_object(Bucket=self.destination_bucket_name, Key=self.ack_file_key)
        ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        self.assertIn("Fatal Error", ack_file_content)
        self.assertIn("Infrastructure Level Response Value - Processing Error", ack_file_content)

    @mock_s3
    def test_lambda_invalid_columns_header_count(self):
        """tests SQS queue is not called when CSV headers are invalid due to missing header"""
        s3_client = self.set_up_s3_buckets_and_upload_file(
            test_file_content=Constants.valid_file_content.replace("PERSON_DOB|", ""),
        )

        # Mock the get_supplier_permissions functions and send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:
            # Call the lambda_handler function
            lambda_handler(event=self.make_event(), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

    @mock_s3
    def test_lambda_invalid_vaccine_type(self):
        """tests SQS queue is not called when file key includes invalid vaccine type"""
        test_file_key = "InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100.csv"
        ack_file_key = "ack/InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100_response.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(test_file_key=test_file_key)

        # Mock the get_supplier_permissionsand send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:
            # Call the lambda_handler function
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_invalid_vaccination(self):
        """tests SQS queue is not called when file key does not include 'Vaccinations'"""
        test_file_key = "Flu_Vaccination_v5_YGM41_20240708T12130100.csv"
        ack_file_key = "ack/Flu_Vaccination_v5_YGM41_20240708T12130100_response.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(test_file_key=test_file_key)

        # Mock the get_supplier_permissions and send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:

            # Call the lambda_handler function
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_invalid_version(self):
        """tests SQS queue is not called when file key includes invalid version"""
        test_file_key = "Flu_Vaccinations_v4_YGM41_20240708T12130100.csv"
        ack_file_key = "ack/Flu_Vaccinations_v4_YGM41_20240708T12130100_response.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(test_file_key=test_file_key)

        # Mock the get_supplier_permissions and send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:
            # Call the lambda_handler function
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_invalid_odscode(self):
        """tests SQS queue is not called when file key includes invalid ods code"""
        test_file_key = "Flu_Vaccinations_v5_InvalidOdsCode_20240708T12130100.csv"
        ack_file_key = "ack/Flu_Vaccinations_v5_InvalidOdsCode_20240708T12130100_response.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(test_file_key=test_file_key)

        # Mock the get_supplier_permissions and send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:
            # Call the lambda_handler function
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_invalid_datetime(self):
        """tests SQS queue is not called when file key includes invalid dateTime"""
        test_file_key = "Flu_Vaccinations_v5_YGM41_20240732T12130100.csv"
        ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240732T12130100_response.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(test_file_key=test_file_key)

        # Mock the get_supplier_permissions functions and send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:
            # Call the lambda_handler function
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_valid_action_flag_permissions(self):
        """tests SQS queue is called when has action flag permissions"""
        s3_client = self.set_up_s3_buckets_and_upload_file(test_file_content=Constants.valid_file_content)

        # Mock the get_supplier_permissions (with return value which includes the requested Flu permissions)
        # and send_to_supplier_queue functions
        with patch(
                "initial_file_validation.get_supplier_permissions",
                return_value=["FLU_CREATE", "FLU_UPDATE", "COVID19_FULL"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:
            # Call the lambda_handler function
            lambda_handler(event=self.make_event(), context=None)

        mock_send_to_supplier_queue.assert_called_once()
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

    @mock_s3
    def test_lambda_invalid_action_flag_permissions(self):
        """tests SQS queue is called when has action flag permissions"""
        s3_client = self.set_up_s3_buckets_and_upload_file(test_file_content=Constants.valid_file_content)

        # Mock the get_supplier_permissions (with return value which doesn't include the requested Flu permissions)
        # and send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_DELETE"]), \
             patch("send_to_supplier_queue.send_to_supplier_queue") as mock_send_to_supplier_queue:
            # Call the lambda_handler function
            lambda_handler(event=self.make_event(), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client)
