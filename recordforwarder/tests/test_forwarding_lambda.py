# pylint: disable=wrong-import-position
# flake8: noqa: E402
"""Tests for forwarding lambda"""

import unittest
from unittest.mock import patch
import os
import sys
from datetime import datetime
from moto import mock_s3
from boto3 import client as boto3_client
from botocore.exceptions import ClientError

# Import local modules after adjusting the path
maindir = os.path.dirname(__file__)
SRCDIR = "../src"
sys.path.insert(0, os.path.abspath(os.path.join(maindir, SRCDIR)))

from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import (
    lambda_success_headers,
    MOCK_ENVIRONMENT_DICT,
    AWS_REGION,
    ResponseBody,
)
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    generate_mock_operation_outcome,
    generate_payload,
    generate_kinesis_message,
    generate_lambda_invocation_side_effect,
)
from forwarding_lambda import forward_lambda_handler, forward_request_to_lambda
from update_ack_file import create_ack_data


s3_client = boto3_client("s3", region_name=AWS_REGION)


@mock_s3
@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestForwardingLambda(unittest.TestCase):

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

        message = {
            "row_id": "test_1",
            "file_key": "file.csv",
            "supplier": "Test_supplier",
            "operation_requested": "CREATE",
            "fhir_json": {"Name": "test"},
        }

        # Mock the create_ack_data method and lambda invocation repsonse payloads
        mock_lambda_payloads = {"CREATE": generate_payload(status_code=201, headers=lambda_success_headers)}
        with (
            patch("update_ack_file.create_ack_data") as mock_create_ack_data,
            patch(
                "utils_for_record_forwarder.lambda_client.invoke",
                side_effect=generate_lambda_invocation_side_effect(mock_lambda_payloads),
            ),
            patch("update_ack_file.s3_client") as mock_s3_client,
        ):
            mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
            # Simulate the case where the ack file does not exist
            mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

            forward_request_to_lambda(message)

        mock_create_ack_data.assert_called_with("20240821T10153000", "test_1", True, None, "test_id")

    @patch("update_ack_file.s3_client")
    def test_forward_request_to_api_new_duplicate(self, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        diagnostics = "The provided identifier: https://supplierABC/identifiers/vacc#test-identifier1 is duplicated"
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        message = {
            "row_id": "test_2",
            "file_key": "file.csv",
            "supplier": "Test_supplier",
            "operation_requested": "CREATE",
            "fhir_json": {"identifier": [{"system": "test_system", "value": "test_value"}]},
        }

        mock_lambda_payloads = {
            "CREATE": generate_payload(status_code=422, body=generate_mock_operation_outcome(diagnostics))
        }
        with (
            patch("update_ack_file.create_ack_data") as mock_create_ack_data,
            patch(
                "utils_for_record_forwarder.lambda_client.invoke",
                side_effect=generate_lambda_invocation_side_effect(mock_lambda_payloads),
            ),
        ):
            forward_request_to_lambda(message)

        mock_create_ack_data.assert_called_with("20240821T10153000", "test_2", False, diagnostics, None)

    @patch("update_ack_file.s3_client")
    def test_forward_request_to_api_update_failure(self, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        diagnostics = (
            "Validation errors: The provided immunization id:test_id doesn't match with the content of the request body"
        )
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        message = {
            "row_id": "test_3",
            "file_key": "file.csv",
            "supplier": "Test_supplier",
            "operation_requested": "UPDATE",
            "fhir_json": {"identifier": [{"system": "test_system", "value": "test_value"}]},
        }

        mock_lambda_payloads = {
            "UPDATE": generate_payload(status_code=422, body=generate_mock_operation_outcome(diagnostics)),
            "SEARCH": generate_payload(status_code=200, body=ResponseBody.id_and_version_found),
        }
        with (
            patch("update_ack_file.create_ack_data") as mock_create_ack_data,
            patch(
                "utils_for_record_forwarder.lambda_client.invoke",
                side_effect=generate_lambda_invocation_side_effect(mock_lambda_payloads),
            ),
        ):
            forward_request_to_lambda(message)

        mock_create_ack_data.assert_called_with("20240821T10153000", "test_3", False, diagnostics, None)

    @patch("utils_for_record_forwarder.lambda_client.invoke")
    @patch("update_ack_file.s3_client")
    def test_forward_request_to_api_update_failure_imms_id_none(self, mock_s3_client, mock_lambda_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_create_ack_data:
            message_body = {
                "row_id": "test_4",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "diagnostics": "Unable to obtain imms_id",
            }
            forward_request_to_lambda(message_body)
            mock_create_ack_data.assert_called_with(
                "20240821T10153000", "test_4", False, "Unable to obtain imms_id", None
            )
            mock_lambda_client.assert_not_called()

    @patch("update_ack_file.s3_client")
    def test_forward_request_to_api_delete_success(self, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        message = {
            "row_id": "test_6",
            "file_key": "file.csv",
            "operation_requested": "DELETE",
            "fhir_json": {"identifier": [{"system": "test_system", "value": "test_value"}]},
        }

        mock_lambda_payloads = {
            "DELETE": generate_payload(status_code=204),
            "SEARCH": generate_payload(status_code=200, body=ResponseBody.id_and_version_found),
        }
        with (
            patch("update_ack_file.create_ack_data") as mock_create_ack_data,
            patch(
                "utils_for_record_forwarder.lambda_client.invoke",
                side_effect=generate_lambda_invocation_side_effect(mock_lambda_payloads),
            ),
        ):
            forward_request_to_lambda(message)

        mock_create_ack_data.assert_called_with(
            "20240821T10153000", "test_6", True, None, "277befd9-574e-47fe-a6ee-189858af3bb0"
        )

    @patch("forwarding_lambda.forward_request_to_lambda")
    def test_forward_lambda_handler(self, mock_forward_request_to_api):
        message_body = {
            "row_id": "test_7",
            "fhir_json": "{}",
            "operation_requested": "CREATE",
            "file_key": "test_file.csv",
        }

        forward_lambda_handler(generate_kinesis_message(message_body), None)
        mock_forward_request_to_api.assert_called_once_with(message_body)

    @patch("forwarding_lambda.forward_request_to_lambda")
    def test_forward_lambda_handler_update(self, mock_forward_request_to_api):
        message_body = {
            "row_id": "test_8",
            "fhir_json": "{}",
            "operation_requested": "UPDATE",
            "file_key": "test_file.csv",
        }
        forward_lambda_handler(generate_kinesis_message(message_body), None)
        mock_forward_request_to_api.assert_called_once_with(message_body)

    @patch("forwarding_lambda.logger")
    def test_forward_lambda_handler_with_exception(self, mock_logger):
        message_body = {
            "row_id": "test_9",
            "fhir_json": "{}",
            "operation_requested": "INVALID OPERATION",
            "file_key": "test_file.csv",
        }
        forward_lambda_handler(generate_kinesis_message(message_body), None)
        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
