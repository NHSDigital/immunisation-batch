"""e2e tests for lambda_handler, including specific tests for action flag permissions"""

from unittest.mock import patch, MagicMock
from unittest import TestCase
from json import loads as json_loads
from typing import Optional
from boto3 import client as boto3_client
from moto import mock_s3, mock_sqs
import json
import os
import sys
maindir = os.path.dirname(__file__)
srcdir = '../src'
sys.path.insert(0, os.path.abspath(os.path.join(maindir, srcdir)))
from file_name_processor import lambda_handler  # noqa: E402
from utils_for_tests.values_for_tests import (  # noqa: E402
    VALID_FILE_CONTENT,
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    VALID_FLU_EMIS_FILE_KEY,
    VALID_FLU_EMIS_ACK_FILE_KEY,
    VALID_RSV_EMIS_FILE_KEY,
    VALID_RSV_EMIS_ACK_FILE_KEY,
    CONFIGS_BUCKET_NAME,
    PERMISSION_JSON,
)


class TestLambdaHandler(TestCase):
    """
    Tests for lambda_handler.
    NOTE: All helper functions default to use valid file content with 'Flu_Vaccinations_v5_YGM41_20240708T12130100.csv'
    as the test_file_key and'ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_InfAck.csv' as the ack_file_key
    """

    def set_up_s3_buckets_and_upload_file(self, file_key: Optional[str] = None, file_content: str = None):
        """
        Sets up the source and destination buckets and uploads the test file to the source bucket.
        Returns the S3 client.
        """
        s3_client = boto3_client("s3", region_name="eu-west-2")

        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})

        s3_client.put_object(
            Bucket=SOURCE_BUCKET_NAME, Key=file_key or VALID_FLU_EMIS_FILE_KEY, Body=file_content or VALID_FILE_CONTENT
        )

        return s3_client

    def make_event(self, file_key: Optional[str] = None):
        """
        Makes an event with s3 bucket name set to SOURCE_BUCKET_NAME and
        and s3 object key set to the file_key if given, else the VALID_FLU_EMIS_FILE_KEY
        """
        return {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": SOURCE_BUCKET_NAME},
                        "object": {"key": (file_key or VALID_FLU_EMIS_FILE_KEY)},
                    }
                }
            ]
        }

    def make_event_configs(self, file_key: Optional[str] = None):
        """
        Makes an event with s3 bucket name set to SOURCE_BUCKET_NAME and
        and s3 object key set to the file_key if given, else the VALID_FLU_EMIS_FILE_KEY
        """
        return {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": CONFIGS_BUCKET_NAME},
                        "object": {"key": (file_key or VALID_FLU_EMIS_FILE_KEY)},
                    }
                }
            ]
        }

    def assert_ack_file_in_destination_s3_bucket(self, s3_client, ack_file_key: Optional[str] = None):
        """Assert that the ack file if given, else the VALID_FLU_EMIS_ACK_FILE_KEY, is in the destination S3 bucket"""
        ack_file_key = ack_file_key or VALID_FLU_EMIS_ACK_FILE_KEY
        ack_files = s3_client.list_objects_v2(Bucket=DESTINATION_BUCKET_NAME)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch.dict(os.environ, {"REDIS_HOST": "localhost", "REDIS_PORT": "6379"})
    @patch("fetch_permissions.redis_client")
    def test_lambda_handler_full_permissions(self, mock_redis_client):
        """Tests lambda function end to end"""
        # set up mock for the permission
        mock_redis_client.get.return_value = json.dumps(PERMISSION_JSON)

        # Set up S3
        s3_client = self.set_up_s3_buckets_and_upload_file()

        # Set up SQS
        sqs_client = boto3_client("sqs", region_name="eu-west-2")
        queue_name = "imms-batch-internal-dev-metadata-queue.fifo"
        attributes = {"FIFOQueue": "true", "ContentBasedDeduplication": "true"}
        queue_url = sqs_client.create_queue(QueueName=queue_name, Attributes=attributes)["QueueUrl"]

        # Mock get_supplier_permissions with full FLU permissions

        response = lambda_handler(self.make_event(), None)

        # Assertions
        self.assertEqual(response["statusCode"], 200)
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

        # Check if the message was sent to the SQS queue
        messages = sqs_client.receive_message(QueueUrl=queue_url, WaitTimeSeconds=1, MaxNumberOfMessages=1)
        self.assertIn("Messages", messages)
        received_message = json_loads(messages["Messages"][0]["Body"])

        # Validate message content
        self.assertEqual(received_message["vaccine_type"], "FLU")
        self.assertEqual(received_message["supplier"], "EMIS")
        self.assertEqual(received_message["timestamp"], "20240708T12130100")
        self.assertEqual(received_message["filename"], "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv")

    @patch("elasticcache.s3_client.get_object")
    @patch("elasticcache.redis_client.set")
    @patch("s3_clients.s3_client.get_object")
    def test_successful_processing_from_configs(self, mock_head_object, mock_redis_set, mock_s3_get_object):
        # Mock S3 head_object response
        mock_head_object.return_value = {"LastModified": MagicMock(strftime=lambda fmt: "20240708T12130100")}

        # Mock S3 get_object response for retrieving file content
        mock_s3_get_object.return_value = {"Body": MagicMock(read=lambda: "mock_file_content".encode("utf-8"))}
        # Invoke the Lambda function with the mocked event
        response = lambda_handler(self.make_event_configs(), None)

        # Assert that S3 get_object was called with the correct parameters
        mock_s3_get_object.assert_called_once_with(Bucket=CONFIGS_BUCKET_NAME, Key=VALID_FLU_EMIS_FILE_KEY)

        # Assert that Redis set was called with the correct key and content
        mock_redis_set.assert_called_once_with(VALID_FLU_EMIS_FILE_KEY, "mock_file_content")

        # Assert Lambda response
        assert response["statusCode"] == 200
        assert response["body"] == '"File content upload to cache from S3 bucket completed"'

    @patch("elasticcache.s3_client.get_object")
    @patch("elasticcache.upload_to_elasticache")
    @patch("s3_clients.s3_client.get_object")
    def test_processing_from_configs_failed(self, mock_head_object, mock_upload_to_elasticache, mock_s3_get_object):
        # Mock S3 head_object response
        mock_head_object.return_value = {"LastModified": MagicMock(strftime=lambda fmt: "20240708T12130100")}

        # Mock S3 get_object response for retrieving file content
        mock_s3_get_object.return_value = {"Body": MagicMock(read=lambda: "mock_file_content".encode("utf-8"))}
        # Simulate an exception being raised when upload_to_elasticache is called
        mock_upload_to_elasticache.side_effect = Exception("Simulated ElastiCache upload failure")
        # Invoke the Lambda function with the mocked event
        response = lambda_handler(self.make_event_configs(), None)

        # Assert that S3 get_object was called with the correct parameters
        mock_s3_get_object.assert_called_once_with(Bucket=CONFIGS_BUCKET_NAME, Key=VALID_FLU_EMIS_FILE_KEY)

        # Assert Lambda response
        assert response["statusCode"] == 400
        assert response["body"] == '"Failed to upload file content to cache from S3 bucket"'

    @mock_s3
    def test_lambda_invalid_csv_header(self):
        """tests SQS queue is not called when CSV headers are invalid due to misspelled header"""
        s3_client = self.set_up_s3_buckets_and_upload_file(
            file_content=VALID_FILE_CONTENT.replace("PERSON_DOB", "PERON_DOB"),
        )

        # Mock the get_supplier_permissions with full FLU permissions. Mock send_to_supplier_queue function.
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), patch(
            "send_sqs_message.send_to_supplier_queue"
        ) as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

        # Validate the content of the ack file to ensure it reports an error due to invalid headers
        ack_file_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=VALID_FLU_EMIS_ACK_FILE_KEY)
        ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        self.assertIn("Fatal Error", ack_file_content)
        self.assertIn("Infrastructure Level Response Value - Processing Error", ack_file_content)

    @mock_s3
    def test_lambda_invalid_columns_header_count(self):
        """tests SQS queue is not called when CSV headers are invalid due to missing header"""
        s3_client = self.set_up_s3_buckets_and_upload_file(
            file_content=VALID_FILE_CONTENT.replace("PERSON_DOB|", ""),
        )

        # Mock the get_supplier_permissions with full FLU permissions. Mock send_to_supplier_queue function.
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), patch(
            "send_sqs_message.send_to_supplier_queue"
        ) as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

    @mock_s3
    def test_lambda_invalid_vaccine_type(self):
        """tests SQS queue is not called when file key includes invalid vaccine type"""
        test_file_key = "InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100.csv"
        ack_file_key = "ack/InvalidVaccineType_Vaccinations_v5_YGM41_20240708T12130100_InfAck.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(file_key=test_file_key)

        # Mock the get_supplier_permissions with full FLU permissions. Mock send_to_supplier_queue function.
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), patch(
            "send_sqs_message.send_to_supplier_queue"
        ) as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_invalid_vaccination(self):
        """tests SQS queue is not called when file key does not include 'Vaccinations'"""
        test_file_key = "Flu_Vaccination_v5_YGM41_20240708T12130100.csv"
        ack_file_key = "ack/Flu_Vaccination_v5_YGM41_20240708T12130100_InfAck.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(file_key=test_file_key)

        # Mock the get_supplier_permissions with full FLU permissions. Mock send_to_supplier_queue function.
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), patch(
            "send_sqs_message.send_to_supplier_queue"
        ) as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_invalid_version(self):
        """tests SQS queue is not called when file key includes invalid version"""
        test_file_key = "Flu_Vaccinations_v4_YGM41_20240708T12130100.csv"
        ack_file_key = "ack/Flu_Vaccinations_v4_YGM41_20240708T12130100_InfAck.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(file_key=test_file_key)

        # Mock the get_supplier_permissions with full FLU permissions. Mock send_to_supplier_queue function.
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), patch(
            "send_sqs_message.send_to_supplier_queue"
        ) as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_invalid_odscode(self):
        """tests SQS queue is not called when file key includes invalid ods code"""
        test_file_key = "Flu_Vaccinations_v5_InvalidOdsCode_20240708T12130100.csv"
        ack_file_key = "ack/Flu_Vaccinations_v5_InvalidOdsCode_20240708T12130100_InfAck.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(file_key=test_file_key)

        # Mock the get_supplier_permissions with full FLU permissions. Mock send_to_supplier_queue function.
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), patch(
            "send_sqs_message.send_to_supplier_queue"
        ) as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    def test_lambda_invalid_datetime(self):
        """tests SQS queue is not called when file key includes invalid dateTime"""
        test_file_key = "Flu_Vaccinations_v5_YGM41_20240732T12130100.csv"
        ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240732T12130100_InfAck.csv"
        s3_client = self.set_up_s3_buckets_and_upload_file(file_key=test_file_key)

        # Mock the get_supplier_permissions with full FLU permissions. Mock send_to_supplier_queue function.
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_FULL"]), patch(
            "send_sqs_message.send_to_supplier_queue"
        ) as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(test_file_key), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

    @mock_s3
    @patch("initial_file_validation.get_permissions_config_json_from_cache")
    def test_lambda_valid_action_flag_permissions(self, mock_get_permissions):
        """tests SQS queue is called when has action flag permissions"""
        # set up mock for the permission when the validation passed
        mock_get_permissions.return_value = {"all_permissions": {"EMIS": ["FLU_FULL"]}}

        s3_client = self.set_up_s3_buckets_and_upload_file(file_content=VALID_FILE_CONTENT)
        # Mock the get_supplier_permissions (with return value which includes the requested Flu permissions)
        # and send_to_supplier_queue functions
        with patch(
            "initial_file_validation.get_supplier_permissions",
            return_value=["FLU_CREATE", "FLU_UPDATE", "COVID19_FULL"],
        ), patch("send_sqs_message.send_to_supplier_queue") as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(), context=None)

        mock_send_to_supplier_queue.assert_called_once()
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

    @mock_s3
    def test_lambda_invalid_action_flag_permissions(self):
        """tests SQS queue is called when has action flag permissions"""
        s3_client = self.set_up_s3_buckets_and_upload_file(file_content=VALID_FILE_CONTENT)

        # Mock the get_supplier_permissions (with return value which doesn't include the requested Flu permissions)
        # and send_to_supplier_queue functions
        with patch("initial_file_validation.get_supplier_permissions", return_value=["FLU_DELETE"]), patch(
            "send_sqs_message.send_to_supplier_queue"
        ) as mock_send_to_supplier_queue:
            lambda_handler(event=self.make_event(), context=None)

        mock_send_to_supplier_queue.assert_not_called()
        self.assert_ack_file_in_destination_s3_bucket(s3_client)

    @mock_s3
    @mock_sqs
    @patch.dict(os.environ, {"REDIS_HOST": "localhost", "REDIS_PORT": "6379"})
    @patch("fetch_permissions.redis_client")
    def test_lambda_handler_full_permissions_rsv(self, mock_redis_client):
        """Tests lambda function end to end for RSV"""
        # set up mock for the permission
        mock_redis_client.get.return_value = json.dumps(PERMISSION_JSON)

        # Set up S3
        s3_client = self.set_up_s3_buckets_and_upload_file(file_key=VALID_RSV_EMIS_FILE_KEY)

        # Set up SQS
        sqs_client = boto3_client("sqs", region_name="eu-west-2")
        queue_name = "imms-batch-internal-dev-metadata-queue.fifo"
        attributes = {"FIFOQueue": "true", "ContentBasedDeduplication": "true"}
        queue_url = sqs_client.create_queue(QueueName=queue_name, Attributes=attributes)["QueueUrl"]
        ack_file_key = VALID_RSV_EMIS_ACK_FILE_KEY

        # Mock get_supplier_permissions with full RSV permissions

        response = lambda_handler(self.make_event(VALID_RSV_EMIS_FILE_KEY), None)

        # Assertions
        self.assertEqual(response["statusCode"], 200)
        self.assert_ack_file_in_destination_s3_bucket(s3_client, ack_file_key)

        # Check if the message was sent to the SQS queue
        messages = sqs_client.receive_message(QueueUrl=queue_url, WaitTimeSeconds=1, MaxNumberOfMessages=1)
        self.assertIn("Messages", messages)
        received_message = json_loads(messages["Messages"][0]["Body"])

        # Validate message content
        self.assertEqual(received_message["vaccine_type"], "RSV")
        self.assertEqual(received_message["supplier"], "EMIS")
        self.assertEqual(received_message["timestamp"], "20240708T12130100")
        self.assertEqual(received_message["filename"], "RSV_Vaccinations_v5_YGM41_20240708T12130100.csv")
