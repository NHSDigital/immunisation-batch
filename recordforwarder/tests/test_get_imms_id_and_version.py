import unittest
from moto import mock_s3
from unittest.mock import patch
from get_imms_id_and_version import get_imms_id_and_version
from errors import IdNotFoundError
from tests.utils_for_recordfowarder_tests.utils_for_recordforwarder_tests import create_mock_api_response


@mock_s3
class TestGetImmsIdAndVersion(unittest.TestCase):

    def test_success(self):
        with patch("get_imms_id_and_version.lambda_client.invoke", return_value=create_mock_api_response(200)):
            fhir_json = {"identifier": [{"value": "a_value", "system": "a_system"}]}
            imms_id, version = get_imms_id_and_version(fhir_json)

        self.assertEqual(imms_id, "277befd9-574e-47fe-a6ee-189858af3bb0")
        self.assertEqual(version, 2)

    def test_failure_1(self):
        with patch("get_imms_id_and_version.lambda_client.invoke", return_value=create_mock_api_response(201)):
            with self.assertRaises(IdNotFoundError):
                fhir_json = {"identifier": [{"value": "a_value", "system": "a_system"}]}
                get_imms_id_and_version(fhir_json)

    def test_failure_2(self):
        with patch(
            "get_imms_id_and_version.lambda_client.invoke", return_value=create_mock_api_response(200, "some diags")
        ):
            with self.assertRaises(IdNotFoundError):
                fhir_json = {"identifier": [{"value": "a_value", "system": "a_system"}]}
                get_imms_id_and_version(fhir_json)
