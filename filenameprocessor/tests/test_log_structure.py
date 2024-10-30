import unittest
from unittest.mock import patch
from boto3 import client as boto3_client
from moto import mock_s3
import json
import os
from typing import Optional
from file_name_processor import lambda_handler
from tests.utils_for_tests.values_for_tests import (
    SOURCE_BUCKET_NAME,
    PERMISSION_JSON,
    DESTINATION_BUCKET_NAME,
    VALID_FILE_CONTENT,
)


def set_up_s3_buckets_and_upload_file(file_key: Optional[str] = None, file_content: str = None):
    """
    Sets up the source and destination buckets and uploads the test file to the source bucket.
    Returns the S3 client.
    """
    s3_client = boto3_client("s3", region_name="eu-west-2")

    for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})

    s3_client.put_object(
        Bucket=SOURCE_BUCKET_NAME,
        Key=file_key or "Flu_Vaccinations_v5_YGM41_20240708T12100100.csv",
        Body=file_content or VALID_FILE_CONTENT,
    )

    return s3_client


class TestFunctionInfoDecorator(unittest.TestCase):

    event_file = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": SOURCE_BUCKET_NAME},
                    "object": {"key": "Flu_Vaccinations_v5_YGM41_20240708T12100100.csv"},
                }
            }
        ]
    }

    @mock_s3
    @patch("initial_file_validation.get_permissions_config_json_from_cache")
    @patch("log_structure.logger")
    @patch("log_structure.firehose_logger")
    @patch.dict(os.environ, {"REDIS_HOST": "localhost", "REDIS_PORT": "6379"})
    @patch("fetch_permissions.redis_client")
    def test_splunk_logger_successful_validation(
        self,
        mock_redis_client,
        mock_firehose_logger,
        mock_logger,
        mock_get_permissions,
    ):
        """Tests the splunk logger is called when file validation is successful"""
        mock_redis_client.get.return_value = json.dumps(PERMISSION_JSON)
        mock_get_permissions.return_value = {"all_permissions": {"EMIS": ["FLU_FULL"]}}
        event = self.event_file

        set_up_s3_buckets_and_upload_file()
        with patch(
            "initial_file_validation.get_supplier_permissions",
            return_value=["FLU_CREATE", "FLU_UPDATE"],
        ), patch("send_sqs_message.send_to_supplier_queue"):
            lambda_handler(event, context=None)

        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        self.assertIn("Successfully sent to SQS queue", result["body"])
        filename = result["file_info"][0]["filename"]
        self.assertEqual(filename, "Flu_Vaccinations_v5_YGM41_20240708T12100100.csv")
        self.assertIn("message_id", result["file_info"][0])
        log_call_args = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call_args)

        self.assertTrue(mock_logger.info.called)
        self.assertTrue(mock_firehose_logger.send_log.called)
        log_data = json.loads(log_call_args)

        self.assertEqual(log_data["function_name"], "lambda_handler")
        self.assertEqual(log_data["status"], 200)

        # Assert - Check Firehose log called
        mock_firehose_logger.send_log.assert_called_with({"event": log_data})
        mock_firehose_logger.send_log.reset_mock()

    @mock_s3
    @patch("initial_file_validation.get_permissions_config_json_from_cache")
    @patch("log_structure.logger")
    @patch("log_structure.firehose_logger")
    @patch.dict(os.environ, {"REDIS_HOST": "localhost", "REDIS_PORT": "6379"})
    @patch("fetch_permissions.redis_client")
    def test_splunk_logger_failed_validation(
        self,
        mock_redis_client,
        mock_firehose_logger,
        mock_logger,
        mock_get_permissions,
    ):
        """Tests the splunk logger is called when file validation is unsuccessful"""
        mock_redis_client.get.return_value = json.dumps(PERMISSION_JSON)
        mock_get_permissions.return_value = {"all_permissions": {"EMIS": ["FLU_FULL"]}}
        event = self.event_file

        set_up_s3_buckets_and_upload_file(file_content=VALID_FILE_CONTENT.replace("PERSON_DOB", "PERON_DOB"))
        with patch(
            "initial_file_validation.get_supplier_permissions",
            return_value=["FLU_CREATE", "FLU_UPDATE"],
        ), patch("send_sqs_message.send_to_supplier_queue") as mock_send_to_supplier_queue:
            lambda_handler(event, context=None)

        result = lambda_handler(event, None)
        mock_send_to_supplier_queue.assert_not_called()
        self.assertEqual(result["statusCode"], 400)
        self.assertIn("Infrastructure Level Response Value - Processing Error", result["body"])
        filename = result["file_info"][0]["filename"]
        self.assertEqual(filename, "Flu_Vaccinations_v5_YGM41_20240708T12100100.csv")
        self.assertIn("message_id", result["file_info"][0])
        log_call_args = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_call_args)

        self.assertTrue(mock_logger.info.called)
        self.assertTrue(mock_firehose_logger.send_log.called)
        log_data = json.loads(log_call_args)

        self.assertEqual(log_data["function_name"], "lambda_handler")
        self.assertEqual(log_data["status"], 400)

        # # Assert - Check Firehose log call
        mock_firehose_logger.send_log.assert_called_with({"event": log_data})
        mock_firehose_logger.send_log.reset_mock()
