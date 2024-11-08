"""Tests for get_imms_id_and_version"""

import unittest
from unittest.mock import patch
from copy import deepcopy
from get_imms_id_and_version import get_imms_id_and_version
from errors import IdNotFoundError
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import (
    generate_lambda_invocation_side_effect,
)
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import (
    test_imms_fhir_json,
    LambdaPayloads,
    MOCK_ENVIRONMENT_DICT,
)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestGetImmsIdAndVersion(unittest.TestCase):
    """
    Tests for get_imms_id_and_version.
    Note that these test mock the lambda invocation, therefore they do not test the interaction with search lambda.
    """

    def test_success(self):
        """Test that imms_id and version are correctly identified from a successful search lambda response."""
        with patch(
            "clients.lambda_client.invoke",
            side_effect=generate_lambda_invocation_side_effect(deepcopy(LambdaPayloads.SEARCH.ID_AND_VERSION_FOUND)),
        ):
            imms_id, version = get_imms_id_and_version(test_imms_fhir_json)

        self.assertEqual(imms_id, "277befd9-574e-47fe-a6ee-189858af3bb0")
        self.assertEqual(version, 2)

    def test_failure_due_to_empty_search_lambda_return(self):
        """Test that an IdNotFoundError is raised for a successful search lambda response which contains no entries."""
        with patch(
            "clients.lambda_client.invoke",
            side_effect=generate_lambda_invocation_side_effect(
                deepcopy(LambdaPayloads.SEARCH.ID_AND_VERSION_NOT_FOUND)
            ),
        ):
            with self.assertRaises(IdNotFoundError):
                get_imms_id_and_version(test_imms_fhir_json)

    def test_failure_due_to_search_lambda_404(self):
        """Test that an IdNotFoundError is raised for an unsuccessful search lambda response."""
        with patch(
            "clients.lambda_client.invoke",
            side_effect=generate_lambda_invocation_side_effect(deepcopy(LambdaPayloads.SEARCH.FAILURE)),
        ):
            with self.assertRaises(IdNotFoundError):
                get_imms_id_and_version(test_imms_fhir_json)
