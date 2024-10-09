import unittest
from unittest.mock import patch
from boto3 import client as boto3_client
import json
from moto import mock_s3
from forwarding_lambda import forward_lambda_handler
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import (
    test_fhir_json,
    AWS_REGION,
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    TEST_FILE_KEY,
    TEST_ACK_FILE_KEY,
)
import base64

s3_client = boto3_client("s3", region_name=AWS_REGION)
kinesis_client = boto3_client("kinesis", region_name=AWS_REGION)


@mock_s3
class TestForwardingLambdaE2E(unittest.TestCase):

    def setup_s3(self):
        """Helper to setup mock S3 buckets and upload test file"""
        s3_client.create_bucket(Bucket=SOURCE_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
        )
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body="test_data")

    def create_kinesis_message(self, message):
        """Helper to create mock kinesis messages"""
        kinesis_encoded_data = base64.b64encode(json.dumps(message).encode("utf-8")).decode("utf-8")
        return {"Records": [{"kinesis": {"data": kinesis_encoded_data}}]}

    def check_ack_file(self, s3_client, expected_content):
        """Helper to check the acknowledgment file content"""
        ack_file_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_ACK_FILE_KEY)
        ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        self.assertIn(expected_content, ack_file_content)

    def execute_test(self, mock_api, message, response_code, expected_content, is_create=True):
        self.setup_s3()
        mock_api.create_immunization.return_value = ("", response_code)
        mock_api.update_immunization.return_value = ("", response_code)

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, expected_content)
        if is_create:
            mock_api.create_immunization.assert_called_once()
        else:
            mock_api.update_immunization.assert_called_once()

    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_lambda_e2e_create_success(self, mock_api):
        message = {
            "message_id": "test_id",
            "fhir_json": test_fhir_json,
            "action_flag": "new",
            "file_name": TEST_FILE_KEY,
        }
        self.execute_test(mock_api, message, 201, "ok")

    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_lambda_e2e_create_duplicate(self, mock_api):
        message = {
            "message_id": "test_id",
            "fhir_json": test_fhir_json,
            "action_flag": "new",
            "file_name": TEST_FILE_KEY,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 422, "fatal-error")

    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_lambda_e2e_create_failed(self, mock_api):
        message = {
            "fhir_json": test_fhir_json,
            "action_flag": "new",
            "file_name": TEST_FILE_KEY,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 400, "fatal-error")

    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_lambda_e2e_none_request(self, mock_api):
        self.setup_s3()
        mock_api.create_immunization.return_value = ("", 201)

        message = {
            "fhir_json": "None",
            "action_flag": "None",
            "file_name": TEST_FILE_KEY,
            "imms_id": "None",
            "version": "None",
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "fatal-error")
        mock_api.create_immunization.assert_not_called()

    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_lambda_e2e_update_success(self, mock_api):
        message = {
            "fhir_json": test_fhir_json,
            "action_flag": "update",
            "file_name": TEST_FILE_KEY,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 200, "ok", is_create=False)

    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_lambda_e2e_update_failed(self, mock_api):
        message = {
            "fhir_json": test_fhir_json,
            "action_flag": "update",
            "file_name": TEST_FILE_KEY,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 400, "fatal-error", is_create=False)

    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_lambda_e2e_delete_success(self, mock_api):
        self.setup_s3()
        mock_api.delete_immunization.return_value = ("", 204)

        message = {
            "fhir_json": test_fhir_json,
            "action_flag": "delete",
            "file_name": TEST_FILE_KEY,
            "imms_id": "test",
            "version": 1,
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "ok")
        mock_api.delete_immunization.assert_called_once()

    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_lambda_e2e_delete_failed(self, mock_api):
        self.setup_s3()
        mock_api.delete_immunization.return_value = ("", 404)

        message = {
            "fhir_json": test_fhir_json,
            "action_flag": "delete",
            "file_name": TEST_FILE_KEY,
            "imms_id": "test",
            "version": 1,
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "fatal-error")
        mock_api.delete_immunization.assert_called_once()

    def test_forward_lambda_e2e_no_permissions(self):
        self.setup_s3()

        message = {
            "fhir_json": "No_Permissions",
            "action_flag": "No_Permissions",
            "file_name": TEST_FILE_KEY,
            "imms_id": "None",
            "version": "None",
            "message_id": "4444-777",
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "fatal-error")


if __name__ == "__main__":
    unittest.main()
