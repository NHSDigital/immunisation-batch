"""Tests for get_imms_id_and_version"""

import unittest
from unittest.mock import patch
from copy import deepcopy
from moto import mock_s3
from get_imms_id_and_version import get_imms_id_and_version
from errors import IdNotFoundError
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    generate_operation_outcome,
    generate_lambda_payload,
)
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import ResponseBody


fhir_json_with_identifier_value_and_system = {"identifier": [{"value": "a_value", "system": "a_system"}]}


@mock_s3
class TestGetImmsIdAndVersion(unittest.TestCase):
    """
    Tests for get_imms_id_and_version. Note that these test mock the lambda invocation, so do not test the
    interaction with search lambda.
    """

    def test_success(self):
        """Test that imms_id and version are correctly identified from a successful search lambda response."""
        with patch(
            "clients.lambda_client.invoke",
            return_value=generate_lambda_payload(status_code=200, body=deepcopy(ResponseBody.id_and_version_found)),
        ):
            imms_id, version = get_imms_id_and_version(fhir_json_with_identifier_value_and_system)

        self.assertEqual(imms_id, "277befd9-574e-47fe-a6ee-189858af3bb0")
        self.assertEqual(version, 2)

    def test_failure_due_to_empty_search_lambda_return(self):
        """Test that an IdNotFoundError is raised for a successful search lambda response which contains no entries."""
        with patch(
            "clients.lambda_client.invoke",
            return_value=generate_lambda_payload(status_code=200, body=deepcopy(ResponseBody.id_and_version_not_found)),
        ):
            with self.assertRaises(IdNotFoundError):
                get_imms_id_and_version(fhir_json_with_identifier_value_and_system)

    def test_failure_due_to_search_lambda_404(self):
        """Test that an IdNotFoundError is raised for an unsuccessful search lambda response."""
        with patch(
            "clients.lambda_client.invoke",
            return_value=generate_lambda_payload(status_code=404, body=generate_operation_outcome("some_diagnostics")),
        ):
            with self.assertRaises(IdNotFoundError):
                get_imms_id_and_version(fhir_json_with_identifier_value_and_system)
