import unittest
from unittest.mock import patch
import boto3
import json
from moto import mock_s3, mock_sqs
from forwarding_lambda import forward_lambda_handler
from src.constants import Constant
import base64


class TestForwardingLambdaE2E(unittest.TestCase):

    def setUp(self):
        self.region_name = "eu-west-2"
        self.source_bucket_name = "immunisation-batch-internal-dev-data-sources"
        self.ack_bucket_name = "immunisation-batch-internal-dev-data-destinations"
        self.test_file_key = "test_file.csv"

    def setup_s3(self):
        """Helper to setup mock S3 buckets and upload test file"""
        s3_client = boto3.client("s3", region_name=self.region_name)
        s3_client.create_bucket(
            Bucket=self.source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": self.region_name},
        )
        s3_client.create_bucket(
            Bucket=self.ack_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": self.region_name},
        )
        s3_client.put_object(Bucket=self.source_bucket_name, Key=self.test_file_key, Body="test_data")
        return s3_client

    def create_kinesis_message(self, message):
        """Helper to create mock kinesis messages"""
        kinesis_encoded_data = base64.b64encode(json.dumps(message).encode("utf-8")).decode("utf-8")
        return {"Records": [{"kinesis": {"data": kinesis_encoded_data}}]}

    def check_ack_file(self, s3_client, expected_content):
        """Helper to check the acknowledgment file content"""
        ack_filename = f'forwardedFile/{self.test_file_key.split(".")[0]}_response.csv'
        ack_file_obj = s3_client.get_object(Bucket=self.ack_bucket_name, Key=ack_filename)
        ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        self.assertIn(expected_content, ack_file_content)

    def execute_test(self, mock_api, message, response_code, expected_content, is_create=True):
        s3_client = self.setup_s3()
        if is_create:
            mock_api.create_immunization.return_value = ("", response_code)
        else:
            mock_api.update_immunization.return_value = ("", response_code)

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, expected_content)
        if is_create:
            mock_api.create_immunization.assert_called_once()
        else:
            mock_api.update_immunization.assert_called_once()

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_create_success(self, mock_api):
        message = {
            "message_id": Constant.test_fhir_json,
            "fhir_json": Constant.test_fhir_json,
            "action_flag": "NEW",
            "file_name": self.test_file_key,
            "imms_id": "None",
            "version": "None",
        }
        self.execute_test(mock_api, message, 201, "ok")

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_create_duplicate(self, mock_api):
        message = {
            "fhir_json": Constant.test_fhir_json,
            "action_flag": "NEW",
            "file_name": self.test_file_key,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 422, "fatal-error")

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_create_failed(self, mock_api):
        message = {
            "fhir_json": Constant.test_fhir_json,
            "action_flag": "NEW",
            "file_name": self.test_file_key,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 400, "fatal-error")

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_none_request(self, mock_api):
        s3_client = self.setup_s3()
        mock_api.create_immunization.return_value = ("", 201)

        message = {
            "fhir_json": "None",
            "action_flag": "None",
            "file_name": self.test_file_key,
            "imms_id": "None",
            "version": "None",
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "fatal-error")
        mock_api.create_immunization.assert_not_called()

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_update_success(self, mock_api):
        message = {
            "fhir_json": Constant.test_fhir_json,
            "action_flag": "UPDATE",
            "file_name": self.test_file_key,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 200, "ok", is_create=False)

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_update_failed(self, mock_api):
        message = {
            "fhir_json": Constant.test_fhir_json,
            "action_flag": "UPDATE",
            "file_name": self.test_file_key,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 400, "fatal-error", is_create=False)

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_delete_success(self, mock_api):
        s3_client = self.setup_s3()
        mock_api.delete_immunization.return_value = ("", 204)

        message = {
            "fhir_json": Constant.test_fhir_json,
            "action_flag": "DELETE",
            "file_name": self.test_file_key,
            "imms_id": "test",
            "version": 1,
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "ok")
        mock_api.delete_immunization.assert_called_once()

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_delete_failed(self, mock_api):
        s3_client = self.setup_s3()
        mock_api.delete_immunization.return_value = ("", 404)

        message = {
            "fhir_json": Constant.test_fhir_json,
            "action_flag": "DELETE",
            "file_name": self.test_file_key,
            "imms_id": "test",
            "version": 1,
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "fatal-error")
        mock_api.delete_immunization.assert_called_once()

    @mock_s3
    @mock_sqs
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_lambda_e2e_no_permissions(self, mock_api):
        s3_client = self.setup_s3()

        message = {
            "fhir_json": "No_Permissions",
            "action_flag": "No_Permissions",
            "file_name": self.test_file_key,
            "imms_id": "None",
            "version": "None",
            "message_id": "4444-777",
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "fatal-error")


if __name__ == "__main__":
    unittest.main()
