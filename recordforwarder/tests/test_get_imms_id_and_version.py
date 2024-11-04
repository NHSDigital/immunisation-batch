"""Tests for get_imms_id_and_version"""

import unittest
from unittest.mock import patch
import json
from io import StringIO
from moto import mock_s3
from get_imms_id_and_version import get_imms_id_and_version
from errors import IdNotFoundError
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    generate_payload,
    response_body_id_and_version_found,
    response_body_id_and_version_not_found,
    generate_mock_operation_outcome,
)


fhir_json_with_identifier_value_and_system = {"identifier": [{"value": "a_value", "system": "a_system"}]}


@mock_s3
class TestGetImmsIdAndVersion(unittest.TestCase):
    """
    Tests for get_imms_id_and_version. Note that these test mock the lambda invocation, so do not test the
    interaction with search lambda.
    """

    def test_success(self):
        """Test that imms_id and version are correctly identified from a successful search lambda response."""
        mock_lambda_response_payload = {
            "Payload": StringIO(json.dumps(generate_payload(200, body=response_body_id_and_version_found)))
        }
        with patch("clients.lambda_client.invoke", return_value=mock_lambda_response_payload):
            imms_id, version = get_imms_id_and_version(fhir_json_with_identifier_value_and_system)

        self.assertEqual(imms_id, "277befd9-574e-47fe-a6ee-189858af3bb0")
        self.assertEqual(version, 2)

    def test_failure_due_to_empty_search_lambda_return(self):
        """Test that an IdNotFoundError is raised for a successful search lambda response which contains no entries."""
        mock_lambda_response_payload = {
            "Payload": StringIO(json.dumps(generate_payload(200, body=response_body_id_and_version_not_found)))
        }
        with patch("clients.lambda_client.invoke", return_value=mock_lambda_response_payload):
            with self.assertRaises(IdNotFoundError):
                get_imms_id_and_version(fhir_json_with_identifier_value_and_system)

    def test_failure_due_to_search_lambda_404(self):
        """Test that an IdNotFoundError is raised for an unsuccessful search lambda response."""
        mock_lambda_response_payload = {
            "Payload": StringIO(
                json.dumps(generate_payload(404, body=generate_mock_operation_outcome("some_diagnostics")))
            )
        }
        with patch("clients.lambda_client.invoke", return_value=mock_lambda_response_payload):
            with self.assertRaises(IdNotFoundError):
                get_imms_id_and_version(fhir_json_with_identifier_value_and_system)
