import unittest
from unittest.mock import patch, MagicMock
from moto import mock_s3
from boto3 import client as boto3_client
import json
from botocore.exceptions import ClientError
from datetime import datetime
import base64
import os
import sys

# Move the sys.path insertion to the top along with other imports
maindir = os.path.dirname(__file__)
srcdir = '../src'
sys.path.insert(0, os.path.abspath(os.path.join(maindir, srcdir)))

# Import other modules after adjusting the path
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import AWS_REGION  # noqa: E402
from forwarding_lambda import forward_lambda_handler, forward_request_to_lambda  # noqa: E402
from utils_for_record_forwarder import get_environment  # noqa: E402
from update_ack_file import create_ack_data  # noqa: E402
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (  # noqa: E402
    create_mock_operation_outcome
)


s3_client = boto3_client("s3", region_name=AWS_REGION)


@mock_s3
class TestForwardingLambda(unittest.TestCase):

    @patch("utils_for_record_forwarder.os.getenv")
    def test_get_environment_internal_dev(self, mock_getenv):
        mock_getenv.return_value = "internal-dev"
        self.assertEqual(get_environment(), "internal-dev")

    @patch("utils_for_record_forwarder.os.getenv")
    def test_get_environment_prod(self, mock_getenv):
        mock_getenv.return_value = "prod"
        self.assertEqual(get_environment(), "prod")

    @patch("utils_for_record_forwarder.os.getenv")
    def test_get_environment_default(self, mock_getenv):
        mock_getenv.return_value = None
        self.assertEqual(get_environment(), "internal-dev")

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

        # Test cas tuples are structured as (test_name, successful_api_response, diagnostics, imms_id, expected output)
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

    @patch("send_request_to_lambda.client")
    @patch("update_ack_file.s3_client")
    def test_forward_request_to_api_new_success(self, mock_s3_client, mock_lambda_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_response = MagicMock()
        mock_response['Payload'].read.return_value = json.dumps({
                "statusCode": 201,
                "headers": {
                    "Location": "https://example.com/immunization/test_id"
                }
            })
        mock_lambda_client.invoke.return_value = mock_response
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        # Mock the create_ack_data method
        with patch("update_ack_file.create_ack_data") as mock_create_ack_data:
            # Prepare the message body for the forward_request_to_lambda function
            message_body = {
                "row_id": "test_1",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "operation_requested": "CREATE",
                "fhir_json": {"Name": "test"},
            }
            # Call the function you are testing
            forward_request_to_lambda(message_body)
            # Check that create_ack_data was called with the correct arguments
            mock_create_ack_data.assert_called_with("20240821T10153000", "test_1", True, None, "test_id")

    @patch("send_request_to_lambda.client")
    @patch("update_ack_file.s3_client")
    def test_forward_request_to_api_new_success_duplicate(self, mock_s3_client, mock_lambda_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_response = MagicMock()
        diagnostics = (
            "The provided identifier: https://supplierABC/identifiers/vacc#test-identifier1 is duplicated"
        )
        mock_response['Payload'].read.return_value = json.dumps({
                "statusCode": 422,
                "body": create_mock_operation_outcome(diagnostics)
            })
        mock_lambda_client.invoke.return_value = mock_response
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_create_ack_data:
            message_body = {
                "row_id": "test_2",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "operation_requested": "CREATE",
                "fhir_json": "{}",
            }
            forward_request_to_lambda(message_body)
            # Check that the data_rows function was called with success status and formatted datetime
            mock_create_ack_data.assert_called_with("20240821T10153000", "test_2", False, diagnostics, None)

    @patch("send_request_to_lambda.client")
    @patch("update_ack_file.s3_client")
    def test_forward_request_to_api_update_failure(self, mock_s3_client, mock_lambda_client):
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_response = MagicMock()
        diagnostics = (
            "Validation errors: The provided immunization id:test_id doesn't match with the content of the request body"
        )
        mock_response['Payload'].read.return_value = json.dumps({
                "statusCode": 422,
                "body": create_mock_operation_outcome(diagnostics)
            })
        mock_lambda_client.invoke.return_value = mock_response
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_create_ack_data:
            message_body = {
                "row_id": "test_3",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "operation_requested": "UPDATE",
                "fhir_json": {"resourceType": "immunization"},
                "imms_id": "imms_id",
                "version": "v1",
            }
            forward_request_to_lambda(message_body)
            mock_create_ack_data.assert_called_with("20240821T10153000", "test_3", False, diagnostics, "imms_id")

    @patch("send_request_to_lambda.client")
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

    @patch("send_request_to_lambda.client")
    @patch("update_ack_file.s3_client")
    def test_forward_request_to_api_delete_success(self, mock_s3_client, mock_lambda_client):
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")
        mock_response = MagicMock()
        mock_response['Payload'].read.return_value = json.dumps({
                "statusCode": 204,
                "headers": {
                    "Location": "https://example.com/immunization/test_id"
                }
            })
        mock_lambda_client.invoke.return_value = mock_response
        with patch("update_ack_file.create_ack_data") as mock_create_ack_data:
            message_body = {
                "row_id": "test_6",
                "file_key": "file.csv",
                "operation_requested": "DELETE",
                "fhir_json": "{}",
                "imms_id": "imms_id",
            }
            forward_request_to_lambda(message_body)
            mock_create_ack_data.assert_called_with("20240821T10153000", "test_6", True, None, "imms_id")

    @patch("forwarding_lambda.forward_request_to_lambda")
    @patch("utils_for_record_forwarder.get_environment")
    def test_forward_lambda_handler(self, mock_get_environment, mock_forward_request_to_api):
        # Mock the environment to return 'internal-dev'
        mock_get_environment.return_value = "internal-dev"

        # Simulate the event data that Lambda would receive
        message_body = {
            "row_id": "test_7",
            "fhir_json": "{}",
            "operation_requested": "CREATE",
            "file_key": "test_file.csv",
        }
        event = {
            "Records": [
                {"kinesis": {"data": base64.b64encode(json.dumps(message_body).encode("utf-8")).decode("utf-8")}}
            ]
        }
        forward_lambda_handler(event, None)
        mock_forward_request_to_api.assert_called_once_with(message_body)

    @patch("forwarding_lambda.forward_request_to_lambda")
    @patch("utils_for_record_forwarder.get_environment")
    def test_forward_lambda_handler_update(self, mock_get_environment, mock_forward_request_to_api):
        mock_get_environment.return_value = "internal-dev"
        message_body = {
            "row_id": "test_8",
            "fhir_json": "{}",
            "operation_requested": "UPDATE",
            "file_key": "test_file.csv",
        }
        event = {
            "Records": [
                {"kinesis": {"data": base64.b64encode(json.dumps(message_body).encode("utf-8")).decode("utf-8")}}
            ]
        }
        forward_lambda_handler(event, None)
        mock_forward_request_to_api.assert_called_once_with(message_body)

    @patch("forwarding_lambda.logger")
    def test_forward_lambda_handler_with_exception(self, mock_logger):
        event = {
            "Records": [
                {"body": json.dumps({"fhir_json": "{}", "action_flag": "invalid_action", "file_key": "test_file.csv"})}
            ]
        }
        forward_lambda_handler(event, None)
        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
