import unittest
from unittest.mock import patch
from boto3 import client as boto3_client
import json
from moto import mock_s3
import os
import sys
import base64
maindir = os.path.dirname(__file__)
srcdir = '../src'
sys.path.insert(0, os.path.abspath(os.path.join(maindir, srcdir)))
from forwarding_lambda import forward_lambda_handler  # noqa: E402
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import (  # noqa: E402
    test_fhir_json,
    AWS_REGION,
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    TEST_FILE_KEY,
    TEST_ACK_FILE_KEY,
    TEST_SUPPLIER,
    TEST_ROW_ID,
)
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import create_mock_api_response  # noqa: E402


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

    def execute_test(self, mock_api, message, response_code, expected_content, mock_diagnostics=None):
        self.setup_s3()
        mock_response = create_mock_api_response(response_code, mock_diagnostics)
        mock_api.invoke.return_value = mock_response
        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, expected_content)

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_create_success(self, mock_api):
        # Set the mock response as the return value of invoke
        message = {
            "row_id": TEST_ROW_ID,
            "fhir_json": test_fhir_json,
            "operation_requested": "CREATE",
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
        }
        self.execute_test(mock_api, message, 201, "OK")

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_create_duplicate(self, mock_api):
        message = {
            "row_id": TEST_ROW_ID,
            "fhir_json": test_fhir_json,
            "operation_requested": "CREATE",
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "imms_id": "test",
            "version": 1,
        }
        mock_diagnostics = (
            "The provided identifier: https://supplierABC/identifiers/vacc#test-identifier1 is duplicated"
        )
        self.execute_test(mock_api, message, 422, "Fatal Error", mock_diagnostics=mock_diagnostics)

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_create_failed(self, mock_api):
        message = {
            "row_id": TEST_ROW_ID,
            "fhir_json": test_fhir_json,
            "operation_requested": "CREATE",
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "imms_id": "test",
            "version": 1,
        }
        mock_diagnostics = "the provided event ID is either missing or not in the expected format."
        self.execute_test(mock_api, message, 400, "Fatal Error", mock_diagnostics=mock_diagnostics)

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_create_multi_line_diagnostics(self, mock_api):
        message = {
            "row_id": TEST_ROW_ID,
            "fhir_json": test_fhir_json,
            "operation_requested": "CREATE",
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "imms_id": "test",
            "version": 1,
        }
        mock_diagnostics = """This a string
                    of diagnostics which spans multiple lines
            and has some carriage returns\n\nand random space"""

        expected_single_line_diagnostics = (
            "This a string of diagnostics which spans multiple lines and has some carriage returns and random space"
        )

        self.setup_s3()
        mock_response = create_mock_api_response(400, mock_diagnostics)
        mock_api.invoke.return_value = mock_response
        mock_api.create_immunization.return_value = mock_response

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        ack_file_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_ACK_FILE_KEY)
        ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        self.assertIn(expected_single_line_diagnostics, ack_file_content)

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_none_request(self, mock_api):
        self.setup_s3()

        message = {
            "row_id": TEST_ROW_ID,
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "diagnostics": "Unsupported file type received as an attachment",
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "Fatal Error")
        mock_api.create_immunization.assert_not_called()

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_update_success(self, mock_api):
        message = {
            "row_id": TEST_ROW_ID,
            "fhir_json": test_fhir_json,
            "operation_requested": "UPDATE",
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "imms_id": "test",
            "version": 1,
        }
        self.execute_test(mock_api, message, 200, "OK")

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_update_failed(self, mock_api):
        message = {
            "row_id": TEST_ROW_ID,
            "fhir_json": test_fhir_json,
            "operation_requested": "UPDATE",
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "imms_id": "test",
            "version": 1,
        }
        mock_diagnstics = "the provided event ID is either missing or not in the expected format."
        self.execute_test(mock_api, message, 400, "Fatal Error", mock_diagnostics=mock_diagnstics)

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_delete_success(self, mock_api):
        self.setup_s3()
        mock_response = create_mock_api_response(204)
        mock_api.invoke.return_value = mock_response

        message = {
            "row_id": TEST_ROW_ID,
            "fhir_json": test_fhir_json,
            "operation_requested": "DELETE",
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "imms_id": "test",
            "version": 1,
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "OK")

    @patch("send_request_to_lambda.client")
    def test_forward_lambda_e2e_delete_failed(self, mock_api):
        self.setup_s3()
        mock_response = create_mock_api_response(404, "not-found")
        mock_api.invoke.return_value = mock_response
        message = {
            "row_id": TEST_ROW_ID,
            "fhir_json": test_fhir_json,
            "operation_requested": "DELETE",
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "imms_id": "test",
            "version": 1,
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "Fatal Error")

    def test_forward_lambda_e2e_no_permissions(self):
        self.setup_s3()

        message = {
            "row_id": TEST_ROW_ID,
            "file_key": TEST_FILE_KEY,
            "supplier": TEST_SUPPLIER,
            "diagnostics": "No permissions for operation",
        }

        kinesis_message = self.create_kinesis_message(message)
        forward_lambda_handler(kinesis_message, None)

        self.check_ack_file(s3_client, "Fatal Error")


if __name__ == "__main__":
    unittest.main()
