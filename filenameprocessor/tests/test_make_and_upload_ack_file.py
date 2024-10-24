"""Tests for make_and_upload_ack_file functions"""

from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
from io import StringIO
from copy import deepcopy
from csv import DictReader
from boto3 import client as boto3_client
from moto import mock_s3
from src.make_and_upload_ack_file import make_ack_data, upload_ack_file, make_and_upload_ack_file
from tests.utils_for_tests.values_for_tests import (
    MOCK_ENVIRONMENT_DICT,
    DESTINATION_BUCKET_NAME,
    VALID_FLU_EMIS_FILE_KEY,
    VALID_FLU_EMIS_ACK_FILE_KEY,
)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestMakeAndUploadAckFile(TestCase):
    """Tests for make_and_upload_ack_file functions"""

    def setUp(self):
        """Set up test values to be used for the tests"""
        self.message_id = str(uuid4())
        self.created_at_formatted_string = "20200101T12345600"
        self.ack_data_validation_passed_and_message_delivered = {
            "MESSAGE_HEADER_ID": self.message_id,
            "HEADER_RESPONSE_CODE": "Success",
            "ISSUE_SEVERITY": "Information",
            "ISSUE_CODE": "OK",
            "ISSUE_DETAILS_CODE": "20013",
            "RESPONSE_TYPE": "Technical",
            "RESPONSE_CODE": "20013",
            "RESPONSE_DISPLAY": "Success",
            "RECEIVED_TIME": self.created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": "",
            "MESSAGE_DELIVERY": True,
        }
        self.ack_data_validation_passed_and_message_not_delivered = {
            "MESSAGE_HEADER_ID": self.message_id,
            "HEADER_RESPONSE_CODE": "Failure",
            "ISSUE_SEVERITY": "Information",
            "ISSUE_CODE": "OK",
            "ISSUE_DETAILS_CODE": "20013",
            "RESPONSE_TYPE": "Technical",
            "RESPONSE_CODE": "10002",
            "RESPONSE_DISPLAY": "Infrastructure Level Response Value - Processing Error",
            "RECEIVED_TIME": self.created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": "",
            "MESSAGE_DELIVERY": False,
        }
        self.ack_data_validation_failed = {
            "MESSAGE_HEADER_ID": self.message_id,
            "HEADER_RESPONSE_CODE": "Failure",
            "ISSUE_SEVERITY": "Fatal",
            "ISSUE_CODE": "Fatal Error",
            "ISSUE_DETAILS_CODE": "10001",
            "RESPONSE_TYPE": "Technical",
            "RESPONSE_CODE": "10002",
            "RESPONSE_DISPLAY": "Infrastructure Level Response Value - Processing Error",
            "RECEIVED_TIME": self.created_at_formatted_string,
            "MAILBOX_FROM": "",
            "LOCAL_ID": "",
            "MESSAGE_DELIVERY": False,
        }

    def test_make_ack_data(self):
        "Tests make_ack_data makes correct ack data based on the input args"
        # Test case tuples are stuctured as (validation_passed, message_delivered, expected_result)
        test_cases = [
            (True, True, self.ack_data_validation_passed_and_message_delivered),
            (True, False, self.ack_data_validation_passed_and_message_not_delivered),
            (False, False, self.ack_data_validation_failed),
            # No need to test validation failed and message delivery passed as this scenario cannot occur
        ]

        for validation_passed, message_delivered, expected_result in test_cases:
            with self.subTest():
                self.assertEqual(
                    make_ack_data(
                        self.message_id, validation_passed, message_delivered, self.created_at_formatted_string
                    ),
                    expected_result,
                )

    @mock_s3
    def test_upload_ack_file(self):
        """Test that upload_ack_file successfully uploads the ack file"""
        # Set up up the ack bucket
        s3_client = boto3_client("s3", region_name="eu-west-2")
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )

        # Test case tuples are stuctured as (ack_data, expected_result)
        test_cases = [
            self.ack_data_validation_passed_and_message_delivered,
            self.ack_data_validation_passed_and_message_not_delivered,
            self.ack_data_validation_failed,
        ]

        # Call the upload_ack_file function
        for ack_data in test_cases:
            with self.subTest():
                upload_ack_file(VALID_FLU_EMIS_FILE_KEY, ack_data)

            # Note that the data downloaded from the CSV will contain the bool as a string
            expected_result = deepcopy(ack_data)
            expected_result["MESSAGE_DELIVERY"] = str(expected_result["MESSAGE_DELIVERY"])

            # Check that the uploaded data is as expected
            ack_file_csv_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=VALID_FLU_EMIS_ACK_FILE_KEY)
            csv_content_string = ack_file_csv_obj["Body"].read().decode("utf-8")
            csv_data = list(DictReader(StringIO(csv_content_string), delimiter="|"))
            self.assertEqual(list(csv_data)[0], expected_result)

    @mock_s3
    def test_make_and_upload_ack_file(self):
        """Test that make_and_upload_ack_file uploads an ack file containing the correct values"""
        # Set up up the ack bucket
        s3_client = boto3_client("s3", region_name="eu-west-2")
        s3_client.create_bucket(
            Bucket=DESTINATION_BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )

        # Test case tuples are stuctured as (validation_passed, message_delivered, expected_result)
        test_cases = [
            (True, True, self.ack_data_validation_passed_and_message_delivered),
            (True, False, self.ack_data_validation_passed_and_message_not_delivered),
            (False, False, self.ack_data_validation_failed),
        ]

        # Call the make_and_upload_ack_file function
        for validation_passed, message_delivered, expected_result in test_cases:
            with self.subTest():
                make_and_upload_ack_file(
                    self.message_id,
                    VALID_FLU_EMIS_FILE_KEY,
                    validation_passed,
                    message_delivered,
                    self.created_at_formatted_string,
                )

            # Note that the data downloaded from the CSV will contain the bool as a string
            expected_result["MESSAGE_DELIVERY"] = str(expected_result["MESSAGE_DELIVERY"])

            # Check that the uploaded data is as expected
            ack_file_csv_obj = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=VALID_FLU_EMIS_ACK_FILE_KEY)
            csv_content_string = ack_file_csv_obj["Body"].read().decode("utf-8")
            csv_data = list(DictReader(StringIO(csv_content_string), delimiter="|"))
            self.assertEqual(list(csv_data)[0], expected_result)
