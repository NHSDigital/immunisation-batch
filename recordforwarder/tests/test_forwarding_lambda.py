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
from forwarding_lambda import forward_lambda_handler, forward_request_to_api, get_environment

s3_client = boto3_client("s3", region_name=AWS_REGION)


@mock_s3
class TestForwardingLambda(unittest.TestCase):

    @patch("forwarding_lambda.os.getenv")
    def test_get_environment_internal_dev(self, mock_getenv):
        mock_getenv.return_value = "internal-dev"
        self.assertEqual(get_environment(), "internal-dev")

    @patch("forwarding_lambda.os.getenv")
    def test_get_environment_prod(self, mock_getenv):
        mock_getenv.return_value = "prod"
        self.assertEqual(get_environment(), "prod")

    @patch("forwarding_lambda.os.getenv")
    def test_get_environment_default(self, mock_getenv):
        mock_getenv.return_value = None
        self.assertEqual(get_environment(), "internal-dev")

    @patch("forwarding_lambda.s3_client")
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_request_to_api_new_success(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.create_immunization.return_value = ("", 201)
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("forwarding_lambda.create_ack_data") as mock_data_rows:
            forward_request_to_api(None, "source-bucket", "file.csv", "new", "{}", "ack-bucket", None, None)
            # Check that the data_rows function was called with success status and formatted datetime
            mock_data_rows.assert_called_with("20240821T10153000", None, True, "20013")
            # Verify that the create_immunization API was called exactly once
            mock_api.create_immunization.assert_called_once()

    @patch("forwarding_lambda.s3_client")
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_request_to_api_new_success_duplicate(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.create_immunization.return_value = ("", 422)
        # Simulate the case where the ack file does not exist
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("forwarding_lambda.create_ack_data") as mock_data_rows:
            forward_request_to_api(None, "source-bucket", "file.csv", "new", "{}", "ack-bucket", None, None)
            # Check that the data_rows function was called with success status and formatted datetime
            mock_data_rows.assert_called_with("20240821T10153000", None, False, "20007", "Duplicate Message received")
            # Verify that the create_immunization API was called exactly once
            mock_api.create_immunization.assert_called_once()

    @patch("forwarding_lambda.s3_client")
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_request_to_api_update_failure(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.update_immunization.return_value = (None, 400)
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("forwarding_lambda.create_ack_data") as mock_data_rows:
            forward_request_to_api(
                None,
                "source-bucket",
                "file.csv",
                "update",
                {"resourceType": "immunization"},
                "ack-bucket",
                "imms_id",
                "v1",
            )
            mock_data_rows.assert_called_with("20240821T10153000", None, False, "20009", "Payload validation failure")
            mock_api.update_immunization.assert_called_once_with(
                "imms_id", "v1", {"resourceType": "immunization", "id": "imms_id"}, None
            )

    @patch("forwarding_lambda.s3_client")
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_request_to_api_update_failure_imms_id_none(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.update_immunization.return_value = (None, 400)
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("forwarding_lambda.create_ack_data") as mock_data_rows:
            forward_request_to_api(None, "source-bucket", "file.csv", "update", "{}", "ack-bucket", "None", "None")
            mock_data_rows.assert_called_with("20240821T10153000", None, False, "20005", "failed in json conversion")
            mock_api.update_immunization.assert_not_called()

    @patch("forwarding_lambda.s3_client")
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_request_to_api_delete_failure_imms_id_none(self, mock_api, mock_s3_client):
        # Mock LastModified as a datetime object
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.update_immunization.return_value = (None, 400)
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("forwarding_lambda.create_ack_data") as mock_data_rows:
            forward_request_to_api(None, "source-bucket", "file.csv", "delete", "{}", "ack-bucket", "None", "None")
            mock_data_rows.assert_called_with("20240821T10153000", None, False, "20005", "failed in json conversion")
            mock_api.delete_immunization.assert_not_called()

    @patch("forwarding_lambda.s3_client")
    @patch("forwarding_lambda.immunization_api_instance")
    def test_forward_request_to_api_delete_success(self, mock_api, mock_s3_client):
        mock_s3_client.head_object.return_value = {"LastModified": datetime(2024, 8, 21, 10, 15, 30)}
        mock_api.delete_immunization.return_value = (None, 204)
        mock_s3_client.get_object.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadObject")

        with patch("forwarding_lambda.create_ack_data") as mock_data_rows:
            forward_request_to_api(None, "source-bucket", "file.csv", "delete", "{}", "ack-bucket", "imms_id", None)
            mock_data_rows.assert_called_with("20240821T10153000", None, True, "20013")
            mock_api.delete_immunization.assert_called_once_with("imms_id", "{}", None)

    @patch("forwarding_lambda.forward_request_to_api")
    @patch("forwarding_lambda.get_environment")
    def test_forward_lambda_handler(self, mock_get_environment, mock_forward_request_to_api):
        # Mock the environment to return 'internal-dev'
        mock_get_environment.return_value = "internal-dev"

        # Simulate the event data that Lambda would receive
        event = {
            "Records": [
                {
                    "kinesis": {
                        "data": base64.b64encode(
                            json.dumps(
                                {
                                    "message_id": "test",
                                    "fhir_json": "{}",
                                    "action_flag": "new",
                                    "file_name": "test_file.csv",
                                }
                            ).encode("utf-8")
                        ).decode("utf-8")
                    }
                }
            ]
        }
        forward_lambda_handler(event, None)
        mock_forward_request_to_api.assert_called_once_with(
            "test",
            "immunisation-batch-internal-dev-data-sources",
            "test_file.csv",
            "new",
            "{}",
            "immunisation-batch-internal-dev-data-destinations",
            None,
            None,
        )

    @patch("forwarding_lambda.forward_request_to_api")
    @patch("forwarding_lambda.get_environment")
    def test_forward_lambda_handler_update(self, mock_get_environment, mock_forward_request_to_api):
        mock_get_environment.return_value = "internal-dev"
        event = {
            "Records": [
                {
                    "kinesis": {
                        "data": base64.b64encode(
                            json.dumps(
                                {
                                    "message_id": "test",
                                    "fhir_json": "{}",
                                    "action_flag": "update",
                                    "file_name": "test_file.csv",
                                }
                            ).encode("utf-8")
                        ).decode("utf-8")
                    }
                }
            ]
        }
        forward_lambda_handler(event, None)
        mock_forward_request_to_api.assert_called_once_with(
            "test",
            "immunisation-batch-internal-dev-data-sources",
            "test_file.csv",
            "update",
            "{}",
            "immunisation-batch-internal-dev-data-destinations",
            None,
            None,
        )

    @patch("forwarding_lambda.logger")
    def test_forward_lambda_handler_with_exception(self, mock_logger):
        event = {
            "Records": [
                {"body": json.dumps({"fhir_json": "{}", "action_flag": "invalid_action", "file_name": "test_file.csv"})}
            ]
        }
        forward_lambda_handler(event, None)
        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
