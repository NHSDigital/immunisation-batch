import unittest
from moto import mock_s3
import json
from unittest.mock import MagicMock, patch
import requests
from get_imms_id_and_version import get_imms_id_and_version
from errors import IdNotFoundError


def create_mock_api_response(status_code: int, diagnostics: str = None) -> requests.Response:
    mock_response = MagicMock()
    if status_code != 200:
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": status_code,
                "body": '{"resourceType": "OperationOutcome", "id": "45b552ca-755a-473f-84df-c7e7767bd2ac",'
                '"issue": [{"severity": "error","code": "error",'
                '"details": {"coding": [{"system": "test", "code": "unknown-error"}]},'
                '"diagnostics": "unknown-error"}]}',
            }
        )
    if diagnostics is None and status_code == 200:
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": status_code,
                "body": '{"resourceType": "Bundle", "type": "searchset",'
                '"entry": [{"resource": {"id": "277befd9-574e-47fe-a6ee-189858af3bb0",'
                '"meta": {"versionId": 2}}}], "total": 1}',
            }
        )
    if diagnostics and status_code == 200:
        mock_response["Payload"].read.return_value = json.dumps(
            {
                "statusCode": status_code,
                "body": '{"resourceType": "Bundle", "type": "searchset",' '"entry": [], "total": 0}',
            }
        )
    return mock_response


@mock_s3
class TestGetImmsIdAndVersion(unittest.TestCase):

    def test_success(self):
        with patch("get_imms_id_and_version.lambda_client.invoke", return_value=create_mock_api_response(200)):
            imms_id, version = get_imms_id_and_version("a_system", "a_value")

        self.assertEqual(imms_id, "277befd9-574e-47fe-a6ee-189858af3bb0")
        self.assertEqual(version, 2)

    def test_failure_1(self):
        with patch("get_imms_id_and_version.lambda_client.invoke", return_value=create_mock_api_response(201)):
            with self.assertRaises(IdNotFoundError):
                get_imms_id_and_version("a_system", "a_value")

    def test_failure_2(self):
        with patch(
            "get_imms_id_and_version.lambda_client.invoke", return_value=create_mock_api_response(200, "some diags")
        ):
            with self.assertRaises(IdNotFoundError):
                get_imms_id_and_version("a_system", "a_value")
