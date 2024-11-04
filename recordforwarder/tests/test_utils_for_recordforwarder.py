"""Tests for utils_for_recordforwarder functions"""

from unittest import TestCase
from unittest.mock import patch
from utils_for_record_forwarder import get_environment
from constants import ACK_HEADERS
from update_ack_file import create_ack_data


class TestUtilsForRecordForwarder(TestCase):
    """Tests for utils_for_recordforwarder functions"""

    def test_ack_headers_match_ack_data_keys(self):
        """Ensures that the ACK_HEADERS found in constants, match the headers given as keys in create_ack_data"""
        self.assertEqual(ACK_HEADERS, list(create_ack_data("TEST", "TEST", True).keys()))

    def test_get_environment(self):
        "Tests that get_environment returns the correct environment"
        # Each test case tuple has the structure (environment, expected_result)
        test_cases = (
            ("internal-dev", "internal-dev"),
            ("int", "int"),
            ("ref", "ref"),
            ("sandbox", "sandbox"),
            ("prod", "prod"),
            ("pr-22", "internal-dev"),
        )

        for environment, expected_result in test_cases:
            with self.subTest(f"SubTest for environment: {environment}"):
                with patch.dict("os.environ", {"ENVIRONMENT": environment}):
                    self.assertEqual(get_environment(), expected_result)
