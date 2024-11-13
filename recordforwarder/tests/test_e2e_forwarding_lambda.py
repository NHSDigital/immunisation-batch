# pylint: disable=wrong-import-position
# flake8: noqa: E402
"""E2e tests for forwarding lambda"""

import unittest
from unittest.mock import patch
from copy import deepcopy
import os
import sys
from boto3 import client as boto3_client
from moto import mock_s3

# Import local modules after adjusting the path
maindir = os.path.dirname(__file__)
SRCDIR = "../src"
sys.path.insert(0, os.path.abspath(os.path.join(maindir, SRCDIR)))

from forwarding_lambda import forward_lambda_handler
from constants import Operations
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import (
    AWS_REGION,
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    MOCK_ENVIRONMENT_DICT,
    TestFile,
    Message,
    LambdaPayloads,
)
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    generate_operation_outcome,
    generate_lambda_payload,
    generate_kinesis_message,
    generate_lambda_invocation_side_effect,
)

s3_client = boto3_client("s3", region_name=AWS_REGION)
kinesis_client = boto3_client("kinesis", region_name=AWS_REGION)

LAMBDA_PAYLOADS = LambdaPayloads()


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@patch("send_request_to_lambda.CREATE_LAMBDA_NAME", "mock_create_imms")
@patch("send_request_to_lambda.UPDATE_LAMBDA_NAME", "mock_update_imms")
@patch("send_request_to_lambda.DELETE_LAMBDA_NAME", "mock_delete_imms")
class TestForwardingLambdaE2E(unittest.TestCase):

    def setUp(self) -> None:
        """Sets up the SOURCE and DESTINATION buckets, and upload the TestFile to the SOURCE bucket"""
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TestFile.FILE_KEY, Body="test_data")

    def tearDown(self) -> None:
        """Deletes the buckets and their contents"""
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            s3_client.delete_bucket(Bucket=bucket_name)

    def check_ack_file(self, expected_content):
        """Helper to check the acknowledgment file content"""
        ack_file_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TestFile.ACK_FILE_KEY)
        ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        self.assertIn(expected_content, ack_file_content)

    def execute_test(self, message, expected_content, mock_lambda_payloads: dict):
        with (
            patch(
                "utils_for_record_forwarder.lambda_client.invoke",
                side_effect=generate_lambda_invocation_side_effect(mock_lambda_payloads),
            ),
            # patch("log_firehose.Forwarder_FirehoseLogger.forwarder_send_log"),
        ):
            forward_lambda_handler(generate_kinesis_message(message), None)

        # self.check_ack_file(expected_content)

    def test_forward_lambda_e2e_successes(self):

        messages = [
            {**deepcopy(Message.create_message), "row_id": "test#1"},
            {**deepcopy(Message.update_message), "row_id": "test#2"},
            {**deepcopy(Message.delete_message), "row_id": "test#3"},
            {**deepcopy(Message.create_message), "row_id": "test#4"},
        ]
        # Mock the lambda invocation to return the correct response
        with (
            patch("utils_for_record_forwarder.lambda_client.invoke") as mock_invoke,
            # patch("log_firehose.Forwarder_FirehoseLogger.forwarder_send_log"),
        ):

            for message in messages:
                mock_invoke.side_effect = generate_lambda_invocation_side_effect(deepcopy(LAMBDA_PAYLOADS.SUCCESS))
                forward_lambda_handler(generate_kinesis_message(message), None)

        # ack_file_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TestFile.ACK_FILE_KEY)
        # ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        # self.assertIn("test#1|OK", ack_file_content)
        # self.assertIn("test#2|OK", ack_file_content)
        # self.assertIn("test#3|OK", ack_file_content)
        # self.assertIn("test#4|OK", ack_file_content)

    def test_forward_lambda_e2e_create_duplicate(self):
        self.execute_test(
            Message.create_message, "Fatal Error", mock_lambda_payloads=deepcopy(LAMBDA_PAYLOADS.CREATE.DUPLICATE)
        )

    def test_forward_lambda_e2e_create_multi_line_diagnostics(self):
        mock_diagnostics = """This a string
                    of diagnostics which spans multiple lines
            and has some carriage returns\n\nand random space"""
        mock_body = generate_operation_outcome(diagnostics=mock_diagnostics)
        mock_lambda_payloads = {Operations.CREATE: generate_lambda_payload(status_code=404, body=mock_body)}
        expected_single_line_diagnostics = (
            "This a string of diagnostics which spans multiple lines and has some carriage returns and random space"
        )
        self.execute_test(Message.create_message, expected_single_line_diagnostics, mock_lambda_payloads)

    def test_forward_lambda_e2e_update_failed_unable_to_get_id(self):
        self.execute_test(
            Message.update_message,
            "Fatal",
            mock_lambda_payloads=deepcopy(LAMBDA_PAYLOADS.SEARCH.ID_AND_VERSION_NOT_FOUND),
        )

    def test_forward_lambda_e2e_update_failed(self):
        self.execute_test(
            Message.update_message,
            "Fatal Error",
            mock_lambda_payloads={
                **deepcopy(LAMBDA_PAYLOADS.UPDATE.MISSING_EVENT_ID),
                **deepcopy(LAMBDA_PAYLOADS.SEARCH.ID_AND_VERSION_FOUND),
            },
        )

    def test_forward_lambda_e2e_delete_failed(self):
        self.execute_test(
            Message.delete_message,
            "Fatal Error",
            mock_lambda_payloads=deepcopy(LAMBDA_PAYLOADS.SEARCH.ID_AND_VERSION_NOT_FOUND),
        )

    @patch("utils_for_record_forwarder.lambda_client.invoke")
    def test_forward_lambda_e2e_none_request(self, mock_api):
        message = {**Message.base_message_fields, "diagnostics": "Unsupported file type received as an attachment"}
        self.execute_test(message, "Fatal Error", mock_lambda_payloads={})
        mock_api.create_immunization.assert_not_called()

    def test_forward_lambda_e2e_no_permissions(self):
        message = {**Message.base_message_fields, "diagnostics": "No permissions for operation"}
        self.execute_test(message, "Fatal Error", mock_lambda_payloads={})


# if __name__ == "__main__":
#     unittest.main()
