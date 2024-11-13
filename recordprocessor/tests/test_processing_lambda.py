import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import json
import csv
import boto3
from moto import mock_s3, mock_kinesis
import os
import sys
from uuid import uuid4
maindir = os.path.dirname(__file__)
srcdir = '../src'
sys.path.insert(0, os.path.abspath(os.path.join(maindir, srcdir)))
from batch_processing import (  # noqa: E402
 main,
 process_csv_to_fhir,
 get_environment,
 validate_content_headers,
 validate_action_flag_permissions)
from make_and_upload_ack_file import make_ack_data  # noqa: E402
from utils_for_recordprocessor import get_csv_content_dict_reader, convert_string_to_dict_reader  # noqa: E402
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (  # noqa: E402
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    AWS_REGION,
    STREAM_NAME,
    MOCK_ENVIRONMENT_DICT,
    TEST_FILE_KEY,
    TEST_ACK_FILE_KEY,
    TEST_INF_ACK_FILE_KEY,
    TEST_EVENT,
    VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE,
    VALID_FILE_CONTENT_WITH_UPDATE,
    TEST_EVENT_PERMISSION,
    VALID_FILE_CONTENT_WITH_DELETE,
    VALID_FILE_CONTENT,
    TestValues,
)

s3_client = boto3.client("s3", region_name=AWS_REGION)
kinesis_client = boto3.client("kinesis", region_name=AWS_REGION)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_kinesis
class TestProcessLambdaFunction(unittest.TestCase):

    def setUp(self) -> None:
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})

        self.results = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": (
                        "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
                        "Immunization?immunization.identifier=https://supplierABC/identifiers/"
                        "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
                    ),
                }
            ],
            "entry": [
                {
                    "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
                    "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
                    "resource": {
                        "resourceType": "Immunization",
                        "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
                        "meta": {"versionId": 1},
                    },
                }
            ],
            "total": 1,
        }, 200
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

    def tearDown(self) -> None:
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            s3_client.delete_bucket(Bucket=bucket_name)

    @staticmethod
    def upload_source_file(file_key, file_content):
        """
        Uploads a test file with the TEST_FILE_KEY (Flu EMIS file) the given file content to the source bucket
        """
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=file_key, Body=file_content)

    @staticmethod
    def setup_kinesis(stream_name=STREAM_NAME):
        """Sets up the kinesis stream. Obtains a shard iterator. Returns the kinesis client and shard iterator"""
        kinesis_client.create_stream(StreamName=stream_name, ShardCount=1)

        # Obtain the first shard
        response = kinesis_client.describe_stream(StreamName=stream_name)
        shards = response["StreamDescription"]["Shards"]
        shard_id = shards[0]["ShardId"]

        # Get a shard iterator (using iterator type "TRIM_HORIZON" to read from the beginning)
        shard_iterator = kinesis_client.get_shard_iterator(
            StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
        )["ShardIterator"]

        return shard_iterator

    def assert_value_in_ack_file(self, value):
        """Downloads the ack file, decodes its content and returns the content"""
        response = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_ACK_FILE_KEY)
        content = response["Body"].read().decode("utf-8")
        self.assertIn(value, content)

    def assert_value_in_inf_ack_file(self, value):
        """Downloads the ack file, decodes its content and returns the content"""
        response = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_INF_ACK_FILE_KEY)
        content = response["Body"].read().decode("utf-8")
        self.assertIn(value, content)

    @patch("batch_processing.process_csv_to_fhir")
    @patch("batch_processing.get_operation_permissions")
    def test_lambda_handler(self, mock_get_operation_permissions, mock_process_csv_to_fhir):
        mock_get_operation_permissions.return_value = {"NEW", "UPDATE", "DELETE"}
        message_body = {"vaccine_type": "COVID19", "supplier": "Pfizer", "filename": "testfile.csv"}

        main(json.dumps(message_body))

        mock_process_csv_to_fhir.assert_called_once_with(incoming_message_body=message_body)

    def test_fetch_file_from_s3(self):
        self.upload_source_file(TEST_FILE_KEY, VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        expected_output = csv.DictReader(StringIO(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE), delimiter="|")
        result, csv_data = get_csv_content_dict_reader(SOURCE_BUCKET_NAME, TEST_FILE_KEY)
        self.assertEqual(list(result), list(expected_output))
        self.assertEqual(csv_data, VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("batch_processing.get_operation_permissions", return_value={"CREATE", "UPDATE", "DELETE"}):
            process_csv_to_fhir(TEST_EVENT)

        # self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_DELETE)

        process_csv_to_fhir(TEST_EVENT_PERMISSION)

        # self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_positive_string_provided(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("batch_processing.get_operation_permissions", return_value={"CREATE", "UPDATE", "DELETE"}):
            process_csv_to_fhir(TEST_EVENT)

        # self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_only_mandatory(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("batch_processing.get_operation_permissions", return_value={"CREATE", "UPDATE", "DELETE"}):
            process_csv_to_fhir(TEST_EVENT)

        # self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_positive_string_not_provided(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("batch_processing.get_operation_permissions", return_value={"CREATE", "UPDATE", "DELETE"}):
            process_csv_to_fhir(TEST_EVENT)

        # self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_paramter_missing(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY,
                             Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE.replace("new", ""))

        with patch("process_row.convert_to_fhir_imms_resource", return_value=({}, True)), patch(
            "batch_processing.get_operation_permissions", return_value={"CREATE", "UPDATE", "DELETE"}
        ):
            process_csv_to_fhir(TEST_EVENT)

        # self.assert_value_in_ack_file("Fatal")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_invalid_headers(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY,
                             Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE.replace("NHS_NUMBER", "NHS_NUMBERS"))
        process_csv_to_fhir(TEST_EVENT)
        self.assert_value_in_inf_ack_file("Fatal")
        mock_send_to_kinesis.assert_not_called()

    def test_validate_content_headers(self):
        "Tests that validate_content_headers returns True for an exact header match and False otherwise"
        # Test case tuples are stuctured as (file_content, expected_result)
        test_cases = [
            (VALID_FILE_CONTENT, True),  # Valid file content
            (VALID_FILE_CONTENT.replace("SITE_CODE", "SITE_COVE"), False),  # Misspelled header
            (VALID_FILE_CONTENT.replace("SITE_CODE|", ""), False),  # Missing header
            (VALID_FILE_CONTENT.replace("PERSON_DOB|", "PERSON_DOB|EXTRA_HEADER|"), False),  # Extra header
        ]

        for file_content, expected_result in test_cases:
            with self.subTest():
                # validate_content_headers takes a csv dict reader as it's input
                test_data = convert_string_to_dict_reader(file_content)
                self.assertEqual(validate_content_headers(test_data), expected_result)

    def test_validate_action_flag_permissions(self):
        """
        Tests that validate_action_flag_permissions returns True if supplier has permissions to perform at least one
        of the requested CRUD operations for the given vaccine type, and False otherwise
        """
        # Set up test file content. Note that VALID_FILE_CONTENT contains one "new" and one "update" ACTION_FLAG.
        valid_file_content = VALID_FILE_CONTENT
        valid_content_new_and_update_lowercase = valid_file_content
        valid_content_new_and_update_uppercase = valid_file_content.replace("new", "NEW").replace("update", "UPDATE")
        valid_content_new_and_update_mixedcase = valid_file_content.replace("new", "New").replace("update", "uPdAte")
        valid_content_new_and_delete_lowercase = valid_file_content.replace("update", "delete")
        valid_content_update_and_delete_lowercase = valid_file_content.replace("new", "delete").replace(
            "update", "UPDATE"
        )

        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions, file_content, expected_result)
        test_cases = [
            # FLU, full permissions, lowercase action flags
            ("FLU", ["FLU_FULL"], valid_content_new_and_update_lowercase, True),
            # FLU, partial permissions, uppercase action flags
            ("FLU", ["FLU_CREATE"], valid_content_new_and_update_uppercase, True),
            # FLU, full permissions, mixed case action flags
            ("FLU", ["FLU_FULL"], valid_content_new_and_update_mixedcase, True),
            # FLU, partial permissions (create)
            ("FLU", ["FLU_DELETE", "FLU_CREATE"], valid_content_new_and_update_lowercase, True),
            # FLU, partial permissions (update)
            ("FLU", ["FLU_UPDATE"], valid_content_new_and_update_lowercase, True),
            # FLU, partial permissions (delete)
            ("FLU", ["FLU_DELETE"], valid_content_new_and_delete_lowercase, True),
            # FLU, no permissions
            ("FLU", ["FLU_UPDATE", "COVID19_FULL"], valid_content_new_and_delete_lowercase, False),
            # COVID19, full permissions
            ("COVID19", ["COVID19_FULL"], valid_content_new_and_delete_lowercase, True),
            # COVID19, partial permissions
            ("COVID19", ["COVID19_UPDATE"], valid_content_update_and_delete_lowercase, True),
            # COVID19, no permissions
            ("COVID19", ["FLU_CREATE", "FLU_UPDATE"], valid_content_update_and_delete_lowercase, False),
            # RSV, full permissions
            ("RSV", ["RSV_FULL"], valid_content_new_and_delete_lowercase, True),
            # RSV, partial permissions
            ("RSV", ["RSV_UPDATE"], valid_content_update_and_delete_lowercase, True),
            # RSV, no permissions
            ("RSV", ["FLU_CREATE", "FLU_UPDATE"], valid_content_update_and_delete_lowercase, False),
            # RSV, full permissions, mixed case action flags
            ("RSV", ["RSV_FULL"], valid_content_new_and_update_mixedcase, True),
        ]

        for vaccine_type, vaccine_permissions, file_content, expected_result in test_cases:
            with self.subTest():
                # validate_action_flag_permissions takes a csv dict reader as one of it's args
                self.assertEqual(
                    validate_action_flag_permissions("TEST_SUPPLIER", vaccine_type, vaccine_permissions, file_content),
                    expected_result,
                )

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_wrong_file_invalid_action_flag_permissions(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY,
                             Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        process_csv_to_fhir(TEST_EVENT_PERMISSION)

        self.assert_value_in_inf_ack_file("Fatal")
        mock_send_to_kinesis.assert_not_called()

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_successful(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_UPDATE)

        with patch("batch_processing.get_operation_permissions", return_value={"CREATE", "UPDATE", "DELETE"}):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_update_request)
            process_csv_to_fhir(TEST_EVENT)

        # self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir_incorrect_permissions(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_UPDATE)

        with patch("batch_processing.get_operation_permissions", return_value={"DELETE"}):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_update_request)
            process_csv_to_fhir(TEST_EVENT)

        # self.assert_value_in_ack_file("No permissions for requested operation")
        mock_send_to_kinesis.assert_called()

    def test_get_environment(self):
        with patch("batch_processing.os.getenv", return_value="internal-dev"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

        with patch("batch_processing.os.getenv", return_value="prod"):
            env = get_environment()
            self.assertEqual(env, "prod")

        with patch("batch_processing.os.getenv", return_value="unknown-env"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

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


if __name__ == "__main__":
    unittest.main()
