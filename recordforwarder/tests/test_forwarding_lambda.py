# pylint: disable=wrong-import-position
# flake8: noqa: E402
"""Tests for forwarding lambda"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from copy import deepcopy
from typing import Generator
from datetime import datetime
from contextlib import contextmanager, ExitStack
from moto import mock_s3
from boto3 import client as boto3_client
from botocore.exceptions import ClientError

# Import local modules after adjusting the path
maindir = os.path.dirname(__file__)
SRCDIR = "../src"
sys.path.insert(0, os.path.abspath(os.path.join(maindir, SRCDIR)))

from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import (
    MOCK_ENVIRONMENT_DICT,
    AWS_REGION,
    Message,
    LambdaPayloads,
    Diagnostics,
)
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    generate_kinesis_message,
    generate_lambda_invocation_side_effect,
)
from forwarding_lambda import forward_lambda_handler, forward_request_to_lambda
from update_ack_file import create_ack_data


s3_client = boto3_client("s3", region_name=AWS_REGION)

LAMBDA_PAYLOADS = LambdaPayloads()


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestForwardingLambda(unittest.TestCase):

    @contextmanager
    def common_contexts_for_forwarding_lambda_tests(
        self, mock_lambda_payloads=None
    ) -> Generator[MagicMock, None, None]:
        """
        A context manager which applies common patching for the tests in the TestForwardingLambda class.
        Yields mock_create_ack_data.
        """
        with ExitStack() as stack:
            stack.enter_context(patch("update_ack_file.s3_client")),  # pylint: disable=expression-not-assigned

            stack.enter_context(
                patch(
                    "update_ack_file.s3_client.head_object",
                    return_value={"LastModified": datetime(2024, 8, 21, 10, 15, 30)},
                )
            )

            # Simulate the case where the ack file does not exist
            stack.enter_context(
                patch(
                    "update_ack_file.s3_client.get_object",
                    side_effect=ClientError({"Error": {"Code": "404"}}, "HeadObject"),
                ),
            )

            if mock_lambda_payloads:
                # Mock lambda.invoke with a different payload for each different lambda
                stack.enter_context(
                    patch(
                        "utils_for_record_forwarder.lambda_client.invoke",
                        side_effect=generate_lambda_invocation_side_effect(mock_lambda_payloads),
                    )
                )

            mock_create_ack_data = stack.enter_context(patch("update_ack_file.create_ack_data"))

            yield mock_create_ack_data

    def test_create_ack_data(self):
        created_at_formatted_string = "20241015T18504900"
        row_id = "test_file_id#1"

        success_ack_data = {
            "MESSAGE_HEADER_ID": row_id,
            "HEADER_RESPONSE_CODE": "OK",
            "ISSUE_SEVERITY": "Information",
            "ISSUE_CODE": "OK",
            "ISSUE_DETAILS_CODE": "30001",
            "RESPONSE_TYPE": "Business",
            "RESPONSE_CODE": "30001",
            "RESPONSE_DISPLAY": "Success",
            "RECEIVED_TIME": created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": "",
            "IMMS_ID": "test_imms_id",
            "OPERATION_OUTCOME": "",
            "MESSAGE_DELIVERY": True,
        }

        failure_ack_data = {
            "MESSAGE_HEADER_ID": row_id,
            "HEADER_RESPONSE_CODE": "Fatal Error",
            "ISSUE_SEVERITY": "Fatal",
            "ISSUE_CODE": "Fatal Error",
            "ISSUE_DETAILS_CODE": "30002",
            "RESPONSE_TYPE": "Business",
            "RESPONSE_CODE": "30002",
            "RESPONSE_DISPLAY": "Business Level Response Value - Processing Error",
            "RECEIVED_TIME": created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": "",
            "IMMS_ID": "",
            "OPERATION_OUTCOME": "Some diagnostics",
            "MESSAGE_DELIVERY": False,
        }

        # Test case tuples are structured as (test_name, successful_api_response, diagnostics, imms_id, expected output)
        test_cases = [
            ("ack data for success", True, None, "test_imms_id", success_ack_data),
            ("ack data for failure", False, "Some diagnostics", "", failure_ack_data),
        ]

        for test_name, successful_api_response, diagnostics, imms_id, expected_output in test_cases:
            with self.subTest(test_name):
                self.assertEqual(
                    create_ack_data(created_at_formatted_string, row_id, successful_api_response, diagnostics, imms_id),
                    expected_output,
                )

    def test_forward_request_to_api_new_success(self):
        with self.common_contexts_for_forwarding_lambda_tests(
            deepcopy(LAMBDA_PAYLOADS.SUCCESS)
        ) as mock_create_ack_data:
            forward_request_to_lambda(deepcopy(Message.create_message))

        # pylint: disable=no-member
        mock_create_ack_data.assert_called_with("20240821T10153000", Message.ROW_ID, True, None, "test_id")

    def test_forward_request_to_api_new_duplicate(self):
        with self.common_contexts_for_forwarding_lambda_tests(
            deepcopy(LAMBDA_PAYLOADS.CREATE.DUPLICATE)
        ) as mock_create_ack_data:
            forward_request_to_lambda(deepcopy(Message.create_message))

        # pylint: disable=no-member
        mock_create_ack_data.assert_called_with("20240821T10153000", Message.ROW_ID, False, Diagnostics.DUPLICATE, None)

    def test_forward_request_to_api_update_failure(self):
        mock_lambda_payloads = {
            **deepcopy(LAMBDA_PAYLOADS.UPDATE.VALIDATION_ERROR),
            **deepcopy(LAMBDA_PAYLOADS.SEARCH.ID_AND_VERSION_FOUND),
        }
        with self.common_contexts_for_forwarding_lambda_tests(mock_lambda_payloads) as mock_create_ack_data:
            forward_request_to_lambda(deepcopy(Message.update_message))

        # pylint: disable=no-member
        mock_create_ack_data.assert_called_with(
            "20240821T10153000", Message.ROW_ID, False, Diagnostics.VALIDATION_ERROR, None
        )

    def test_forward_request_to_api_update_failure_imms_id_none(self):
        with (
            self.common_contexts_for_forwarding_lambda_tests() as mock_create_ack_data,
            patch("utils_for_record_forwarder.lambda_client.invoke") as mock_lambda_client,
        ):
            forward_request_to_lambda(Message.diagnostics_message)

        # pylint: disable=no-member
        mock_create_ack_data.assert_called_with("20240821T10153000", Message.ROW_ID, False, Message.DIAGNOSTICS, None)
        mock_lambda_client.assert_not_called()

    def test_forward_request_to_api_delete_success(self):
        with self.common_contexts_for_forwarding_lambda_tests(
            deepcopy(LAMBDA_PAYLOADS.SUCCESS)
        ) as mock_create_ack_data:
            forward_request_to_lambda(deepcopy(Message.delete_message))

        # pylint: disable=no-member
        mock_create_ack_data.assert_called_with(
            "20240821T10153000", Message.ROW_ID, True, None, "277befd9-574e-47fe-a6ee-189858af3bb0"
        )

    def test_forward_lambda_handler(self):
        for message in [
            deepcopy(Message.create_message),
            deepcopy(Message.update_message),
            deepcopy(Message.delete_message),
        ]:
            with patch("forwarding_lambda.forward_request_to_lambda") as mock_forward_request_to_api:
                forward_lambda_handler(generate_kinesis_message(message), None)
            mock_forward_request_to_api.assert_called_once_with(message)

    def test_forward_lambda_handler_with_exception(self):
        message_body = {**deepcopy(Message.create_message), "operation_request": "INVALID_OPERATION"}
        with patch("forwarding_lambda.logger") as mock_logger:
            forward_lambda_handler(generate_kinesis_message(message_body), None)
        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
