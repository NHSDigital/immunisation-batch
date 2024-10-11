import unittest
from unittest.mock import patch
from moto import mock_s3
from boto3 import client as boto3_client
import json
from botocore.exceptions import ClientError
from datetime import datetime
import base64
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import AWS_REGION

# Assuming the script is named 'forwarding_lambda.py'
from forwarding_lambda import forward_lambda_handler, forward_request_to_api
from utils_for_record_forwarder import get_environment

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

    @patch("update_ack_file.s3_client")
    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_request_to_api_new_success(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.create_immunization.return_value = ("", 201)
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_data_rows:
            message_body = {
                "row_id": "test_1",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "operation_requested": "CREATE",
                "fhir_json": "{}",
            }
            forward_request_to_api(message_body)
            # Check that the data_rows function was called with success status and formatted datetime
            mock_data_rows.assert_called_with("20240821T10153000", "test_1", True, "20013", None)
            # Verify that the create_immunization API was called exactly once
            mock_api.create_immunization.assert_called_once()

    @patch("update_ack_file.s3_client")
    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_request_to_api_new_success_duplicate(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.create_immunization.return_value = ("", 422)
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_data_rows:
            message_body = {
                "row_id": "test_2",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "operation_requested": "CREATE",
                "fhir_json": "{}",
            }
            forward_request_to_api(message_body)
            # Check that the data_rows function was called with success status and formatted datetime
            mock_data_rows.assert_called_with(
                "20240821T10153000", "test_2", False, "20007", "Duplicate Message received"
            )
            # Verify that the create_immunization API was called exactly once
            mock_api.create_immunization.assert_called_once()

    @patch("update_ack_file.s3_client")
    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_request_to_api_update_failure(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.update_immunization.return_value = (None, 400)
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_data_rows:
            message_body = {
                "row_id": "test_3",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "operation_requested": "UPDATE",
                "fhir_json": {"resourceType": "immunization"},
                "imms_id": "imms_id",
                "version": "v1",
            }
            forward_request_to_api(message_body)
            mock_data_rows.assert_called_with(
                "20240821T10153000", "test_3", False, "20009", "Payload validation failure"
            )
            mock_api.update_immunization.assert_called_once_with(
                "imms_id", "v1", {"resourceType": "immunization", "id": "imms_id"}, "Test_supplier"
            )

    @patch("update_ack_file.s3_client")
    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_request_to_api_update_failure_imms_id_none(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.update_immunization.return_value = (None, 400)
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_data_rows:
            message_body = {
                "row_id": "test_4",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "diagnostics": "Unable to obtain imms_id",
            }
            forward_request_to_api(message_body)
            mock_data_rows.assert_called_with("20240821T10153000", "test_4", False, "20005", "Unable to obtain imms_id")
            mock_api.update_immunization.assert_not_called()

    @patch("update_ack_file.s3_client")
    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_request_to_api_delete_failure_imms_id_none(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.update_immunization.return_value = (None, 400)
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_data_rows:
            message_body = {
                "row_id": "test_5",
                "file_key": "file.csv",
                "supplier": "Test_supplier",
                "diagnostics": "Unable to obtain imms_id",
            }
            forward_request_to_api(message_body)
            mock_data_rows.assert_called_with("20240821T10153000", "test_5", False, "20005", "Unable to obtain imms_id")
            mock_api.delete_immunization.assert_not_called()

    @patch("update_ack_file.s3_client")
    @patch("send_request_to_api.immunization_api_instance")
    def test_forward_request_to_api_delete_success(self, mock_api, mock_s3_client):
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.delete_immunization.return_value = (None, 204)
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("update_ack_file.create_ack_data") as mock_data_rows:
            message_body = {
                "row_id": "test_6",
                "file_key": "file.csv",
                "operation_requested": "DELETE",
                "fhir_json": "{}",
                "imms_id": "imms_id",
            }
            forward_request_to_api(message_body)
            mock_data_rows.assert_called_with("20240821T10153000", "test_6", True, "20013", None)
            mock_api.delete_immunization.assert_called_once_with("imms_id", "{}", None)

    @patch("forwarding_lambda.forward_request_to_api")
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

    @patch("forwarding_lambda.forward_request_to_api")
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
