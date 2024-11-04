# pylint: disable=wrong-import-position
# flake8: noqa: E402
"""E2e tests for forwarding lambda"""

import unittest
from unittest.mock import patch
import json
from io import StringIO
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
    test_fhir_json,
    AWS_REGION,
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    TEST_FILE_KEY,
    TEST_ACK_FILE_KEY,
    base_message_fields,
    lambda_success_headers,
    MOCK_ENVIRONMENT_DICT,
)
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    response_body_id_and_version_found,
    response_body_id_and_version_not_found,
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
        s3_client.create_bucket(Bucket=SOURCE_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
        )
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body="test_data")

    def check_ack_file(self, expected_content):
        """Helper to check the acknowledgment file content"""
        ack_file_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_ACK_FILE_KEY)
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

    def test_forward_lambda_e2e_update_failed_unable_to_get_id(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "UPDATE"}
        mock_lambda_payloads = {
            "SEARCH": generate_payload(status_code=200, body=response_body_id_and_version_not_found),
        }
        self.execute_test(message, "Fatal", mock_lambda_payloads)

    def test_forward_lambda_e2e_create_success(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "CREATE"}
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=201, headers=lambda_success_headers)}
        self.execute_test(message, "OK", mock_lambda_payloads=mock_lambda_payloads)

    def test_forward_lambda_e2e_create_duplicate(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "CREATE"}
        mock_diagnostics = (
            "The provided identifier: https://supplierABC/identifiers/vacc#test-identifier1 is duplicated"
        )
        mock_body = generate_mock_operation_outcome(diagnostics=mock_diagnostics, code="duplicate")
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=422, body=mock_body)}
        self.execute_test(message, "Fatal Error", mock_lambda_payloads=mock_lambda_payloads)

    def test_forward_lambda_e2e_create_failed(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "CREATE"}
        mock_diagnostics = "the provided event ID is either missing or not in the expected format."
        mock_body = generate_mock_operation_outcome(diagnostics=mock_diagnostics, code="duplicate")
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=400, body=mock_body)}
        self.execute_test(message, "Fatal Error", mock_lambda_payloads=mock_lambda_payloads)

    def test_forward_lambda_e2e_create_multi_line_diagnostics(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "CREATE"}
        mock_diagnostics = """This a string
                    of diagnostics which spans multiple lines
            and has some carriage returns\n\nand random space"""
        mock_body = generate_mock_operation_outcome(diagnostics=mock_diagnostics)
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=404, body=mock_body)}
        expected_single_line_diagnostics = (
            "This a string of diagnostics which spans multiple lines and has some carriage returns and random space"
        )
        self.execute_test(message, expected_single_line_diagnostics, mock_lambda_payloads)

    @patch("utils_for_record_forwarder.lambda_client.invoke")
    def test_forward_lambda_e2e_none_request(self, mock_api):
        self.setup_s3()
        message = {**base_message_fields, "diagnostics": "Unsupported file type received as an attachment"}

        forward_lambda_handler(generate_kinesis_message(message), None)

        self.check_ack_file("Fatal Error")
        mock_api.create_immunization.assert_not_called()

    def test_forward_lambda_e2e_update_success(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "UPDATE"}
        mock_lambda_payloads = {
            "UPDATE": generate_payload(200),
            "SEARCH": generate_payload(200, body=response_body_id_and_version_found),
        }
        self.execute_test(message, "OK", mock_lambda_payloads)

    def test_forward_lambda_e2e_update_failed(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "UPDATE"}
        mock_diagnstics = "the provided event ID is either missing or not in the expected format."
        mock_lambda_payloads = {
            "UPDATE": generate_payload(400, body=generate_mock_operation_outcome(mock_diagnstics)),
            "SEARCH": generate_payload(200, body=response_body_id_and_version_found),
        }
        self.execute_test(message, "Fatal Error", mock_lambda_payloads)

    def test_forward_lambda_e2e_delete_success(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "DELETE"}
        mock_lambda_payloads = {
            "DELETE": generate_payload(204),
            "SEARCH": generate_payload(200, body=response_body_id_and_version_found),
        }
        self.execute_test(message, "OK", mock_lambda_payloads)

    def test_forward_lambda_e2e_delete_failed(self):
        message = {**base_message_fields, "fhir_json": test_fhir_json, "operation_requested": "DELETE"}
        mock_diagnstics = "the provided event ID is either missing or not in the expected format."
        mock_lambda_payloads = {
            "UPDATE": generate_payload(404, body=generate_mock_operation_outcome(mock_diagnstics, code="not-found")),
            "SEARCH": generate_payload(200, body=response_body_id_and_version_not_found),
        }
        self.execute_test(message, "Fatal Error", mock_lambda_payloads)

    def test_forward_lambda_e2e_no_permissions(self):
        self.setup_s3()
        message = {**base_message_fields, "diagnostics": "No permissions for operation"}

        forward_lambda_handler(generate_kinesis_message(message), None)

        self.check_ack_file("Fatal Error")


if __name__ == "__main__":
    unittest.main()
