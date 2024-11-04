# pylint: disable=wrong-import-position
# flake8: noqa: E402
"""E2e tests for forwarding lambda"""

import unittest
from unittest.mock import patch
import os
import sys
from boto3 import client as boto3_client
from moto import mock_s3

# Import local modules after adjusting the path
maindir = os.path.dirname(__file__)
SRCDIR = "../src"
sys.path.insert(0, os.path.abspath(os.path.join(maindir, SRCDIR)))

from forwarding_lambda import forward_lambda_handler
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import (
    AWS_REGION,
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    lambda_success_headers,
    MOCK_ENVIRONMENT_DICT,
    TestFile,
    Message,
    ResponseBody,
)
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    generate_mock_operation_outcome,
    generate_payload,
    generate_kinesis_message,
    generate_lambda_invocation_side_effect,
)

s3_client = boto3_client("s3", region_name=AWS_REGION)
kinesis_client = boto3_client("kinesis", region_name=AWS_REGION)


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestForwardingLambdaE2E(unittest.TestCase):

    def setup_s3(self):
        """Helper to setup mock S3 buckets and upload test file"""
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TestFile.FILE_KEY, Body="test_data")

    def check_ack_file(self, expected_content):
        """Helper to check the acknowledgment file content"""
        ack_file_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TestFile.ACK_FILE_KEY)
        ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        self.assertIn(expected_content, ack_file_content)

    def execute_test(self, message, expected_content, mock_lambda_payloads: dict):
        self.setup_s3()

        with patch(
            "utils_for_record_forwarder.lambda_client.invoke",
            side_effect=generate_lambda_invocation_side_effect(mock_lambda_payloads),
        ):
            forward_lambda_handler(event=generate_kinesis_message(message), _=None)

        self.check_ack_file(expected_content)

    def test_forward_lambda_e2e_create_success(self):
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=201, headers=lambda_success_headers)}
        self.execute_test(Message.create_message, "OK", mock_lambda_payloads=mock_lambda_payloads)

    def test_forward_lambda_e2e_create_duplicate(self):
        mock_diagnostics = (
            "The provided identifier: https://supplierABC/identifiers/vacc#test-identifier1 is duplicated"
        )
        mock_body = generate_mock_operation_outcome(diagnostics=mock_diagnostics, code="duplicate")
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=422, body=mock_body)}
        self.execute_test(Message.create_message, "Fatal Error", mock_lambda_payloads=mock_lambda_payloads)

    def test_forward_lambda_e2e_create_failed(self):
        mock_diagnostics = "the provided event ID is either missing or not in the expected format."
        mock_body = generate_mock_operation_outcome(diagnostics=mock_diagnostics, code="duplicate")
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=400, body=mock_body)}
        self.execute_test(Message.create_message, "Fatal Error", mock_lambda_payloads=mock_lambda_payloads)

    def test_forward_lambda_e2e_create_multi_line_diagnostics(self):
        mock_diagnostics = """This a string
                    of diagnostics which spans multiple lines
            and has some carriage returns\n\nand random space"""
        mock_body = generate_mock_operation_outcome(diagnostics=mock_diagnostics)
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=404, body=mock_body)}
        expected_single_line_diagnostics = (
            "This a string of diagnostics which spans multiple lines and has some carriage returns and random space"
        )
        self.execute_test(Message.create_message, expected_single_line_diagnostics, mock_lambda_payloads)

    def test_forward_lambda_e2e_update_success(self):
        mock_lambda_payloads = {
            "UPDATE": generate_payload(200),
            "SEARCH": generate_payload(200, body=ResponseBody.id_and_version_found),
        }
        self.execute_test(Message.update_message, "OK", mock_lambda_payloads)

    def test_forward_lambda_e2e_update_failed_unable_to_get_id(self):
        mock_lambda_payloads = {
            "SEARCH": generate_payload(status_code=200, body=ResponseBody.id_and_version_not_found),
        }
        self.execute_test(Message.update_message, "Fatal", mock_lambda_payloads)

    def test_forward_lambda_e2e_update_failed(self):
        mock_diagnstics = "the provided event ID is either missing or not in the expected format."
        mock_lambda_payloads = {
            "UPDATE": generate_payload(400, body=generate_mock_operation_outcome(mock_diagnstics)),
            "SEARCH": generate_payload(200, body=ResponseBody.id_and_version_found),
        }
        self.execute_test(Message.update_message, "Fatal Error", mock_lambda_payloads)

    def test_forward_lambda_e2e_delete_success(self):
        mock_lambda_payloads = {
            "DELETE": generate_payload(204),
            "SEARCH": generate_payload(200, body=ResponseBody.id_and_version_found),
        }
        self.execute_test(Message.delete_message, "OK", mock_lambda_payloads)

    def test_forward_lambda_e2e_delete_failed(self):
        mock_diagnstics = "the provided event ID is either missing or not in the expected format."
        mock_lambda_payloads = {
            "UPDATE": generate_payload(404, body=generate_mock_operation_outcome(mock_diagnstics, code="not-found")),
            "SEARCH": generate_payload(200, body=ResponseBody.id_and_version_not_found),
        }
        self.execute_test(Message.delete_message, "Fatal Error", mock_lambda_payloads)

    @patch("utils_for_record_forwarder.lambda_client.invoke")
    def test_forward_lambda_e2e_none_request(self, mock_api):
        self.setup_s3()
        message = {**Message.base_message_fields, "diagnostics": "Unsupported file type received as an attachment"}

        forward_lambda_handler(generate_kinesis_message(message), None)

        self.check_ack_file("Fatal Error")
        mock_api.create_immunization.assert_not_called()

    def test_forward_lambda_e2e_no_permissions(self):
        self.setup_s3()
        message = {**Message.base_message_fields, "diagnostics": "No permissions for operation"}

        forward_lambda_handler(generate_kinesis_message(message), None)

        self.check_ack_file("Fatal Error")


if __name__ == "__main__":
    unittest.main()
