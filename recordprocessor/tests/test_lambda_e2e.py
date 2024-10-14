"E2e tests for recordprocessor"

import unittest
import json
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from copy import deepcopy
from moto import mock_s3, mock_kinesis
from boto3 import client as boto3_client
from src.batch_processing import main
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    CONFIG_BUCKET_NAME,
    PERMISSIONS_FILE_KEY,
    AWS_REGION,
    VALID_FILE_CONTENT_WITH_NEW,
    VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE,
    VALID_FILE_CONTENT_WITH_UPDATE_AND_DELETE,
    VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE_AND_DELETE,
    TEST_ID,
    TEST_VERSION,
    API_RESPONSE_WITH_ID_AND_VERSION,
    API_RESPONSE_WITHOUT_ID_AND_VERSION,
    API_RESPONSE_WITHOUT_VERSION,
    STREAM_NAME,
    TEST_ACK_FILE_KEY,
    TEST_EVENT_DUMPED,
    TEST_FILE_KEY,
    TEST_SUPPLIER,
    TEST_FILE_ID,
    TEST_UNIQUE_ID,
    TEST_DATE,
    MOCK_ENVIRONMENT_DICT,
    MOCK_PERMISSIONS,
)

s3_client = boto3_client("s3", region_name=AWS_REGION)
kinesis_client = boto3_client("kinesis", region_name=AWS_REGION)

yesterday = datetime.now(timezone.utc) - timedelta(days=1)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_kinesis
class TestRecordProcessor(unittest.TestCase):
    """E2e tests for RecordProcessor"""

    def setUp(self) -> None:
        # Tests run too quickly for cache to work. The workaround is to set _cached_last_modified to an earlier time
        # than the tests are run so that the _cached_json_data will always be updated by the test

        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME, CONFIG_BUCKET_NAME]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})

        kinesis_client.create_stream(StreamName=STREAM_NAME, ShardCount=1)

    def tearDown(self) -> None:
        # Delete all of the buckets (the contents of each bucket must be deleted first)
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            s3_client.delete_bucket(Bucket=bucket_name)

        # Delete the kinesis stream
        try:
            kinesis_client.delete_stream(StreamName=STREAM_NAME, EnforceConsumerDeletion=True)
        except kinesis_client.exceptions.ResourceNotFoundException:
            pass

    @staticmethod
    def upload_files(sourc_file_content, mock_permissions=MOCK_PERMISSIONS):  # pylint: disable=dangerous-default-value
        """
        Uploads a test file with the TEST_FILE_KEY (Flu EMIS file) the given file content to the source bucket
        """
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=sourc_file_content)
        s3_client.put_object(Bucket=CONFIG_BUCKET_NAME, Key=PERMISSIONS_FILE_KEY, Body=json.dumps(mock_permissions))

    @staticmethod
    def get_shard_iterator(stream_name=STREAM_NAME):
        """Obtains and returns a shard iterator"""
        # Obtain the first shard
        response = kinesis_client.describe_stream(StreamName=stream_name)
        shards = response["StreamDescription"]["Shards"]
        shard_id = shards[0]["ShardId"]

        # Get a shard iterator (using iterator type "TRIM_HORIZON" to read from the beginning)
        return kinesis_client.get_shard_iterator(
            StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
        )["ShardIterator"]

    @staticmethod
    def get_ack_file_content():
        """Downloads the ack file, decodes its content and returns the decoded content"""
        response = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_ACK_FILE_KEY)
        return response["Body"].read().decode("utf-8")

    def make_assertions(self, test_cases):
        """
        The input is a list of test_case tuples where each tuple is structured as
        (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success).
        The standard key-value pairs
        {row_id: {TEST_FILE_ID}#{index+1}, file_key: TEST_FILE_KEY, supplier: TEST_SUPPLIER} are added to the
        expected_kinesis_data dictionary before assertions are made.
        For each index, assertions will be made on the record found at the given index in the kinesis response.
        Assertions made:
        * Kinesis PartitionKey is TEST_SUPPLIER
        * Kinesis SequenceNumber is index + 1
        * Kinesis ApproximateArrivalTimestamp is later than the timestamp for the preceeding data row
        * Where expected_success is True:
            - "fhir_json" key is found in the Kinesis data
            - Kinesis Data is equal to the expected_kinesis_data when ignoring the "fhir_json"
            - "{TEST_FILE_ID}#{index+1}|ok" is found in the ack file
        * Where expected_success is False:
            - Kinesis Data is equal to the expected_kinesis_data
            - "{TEST_FILE_ID}#{index+1}|fatal-error" is found in the ack file
        """

        ack_file_content = self.get_ack_file_content()
        kinesis_records = kinesis_client.get_records(ShardIterator=self.get_shard_iterator(), Limit=10)["Records"]
        previous_approximate_arrival_time_stamp = yesterday  # Initialise with a time prior to the running of the test
        key_to_ignore = "fhir_json"  # TODO: Add unit tests for convert_to_fhir_json as this is not tested in e2e

        for test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success in test_cases:
            with self.subTest(test_name):

                kinesis_record = kinesis_records[index]
                self.assertEqual(kinesis_record["PartitionKey"], TEST_SUPPLIER)
                self.assertEqual(kinesis_record["SequenceNumber"], f"{index+1}")

                # Ensure that arrival times are sequential
                approximate_arrival_timestamp = kinesis_record["ApproximateArrivalTimestamp"]
                self.assertGreater(approximate_arrival_timestamp, previous_approximate_arrival_time_stamp)
                previous_approximate_arrival_time_stamp = approximate_arrival_timestamp

                kinesis_data = json.loads(kinesis_record["Data"].decode("utf-8"))
                expected_kinesis_data = {
                    "row_id": f"{TEST_FILE_ID}#{index+1}",
                    "file_key": TEST_FILE_KEY,
                    "supplier": TEST_SUPPLIER,
                    **expected_kinesis_data_ignoring_fhir_json,
                }
                if expect_success:
                    self.assertIn(key_to_ignore, kinesis_data)
                    kinesis_data.pop(key_to_ignore)
                    self.assertEqual(kinesis_data, expected_kinesis_data)
                    self.assertIn(f"{TEST_FILE_ID}#{index+1}|ok", ack_file_content)
                else:
                    self.assertEqual(kinesis_data, expected_kinesis_data)
                    self.assertIn(f"{TEST_FILE_ID}#{index+1}|fatal-error", ack_file_content)

    def test_e2e_success(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier has
        full permissions.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE_AND_DELETE)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION):
            main(TEST_EVENT_DUMPED)

        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        test_cases = [
            ("CREATE success", 0, {"operation_requested": "CREATE"}, True),
            ("UPDATE success", 1, {"operation_requested": "UPDATE", "imms_id": TEST_ID, "version": TEST_VERSION}, True),
            ("DELETE success", 2, {"operation_requested": "DELETE", "imms_id": TEST_ID}, True),
        ]
        self.make_assertions(test_cases)

    def test_e2e_no_permissions(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier does not have
        any permissions.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE_AND_DELETE)
        event = deepcopy(TEST_EVENT_DUMPED)
        test_event = json.loads(event)
        test_event["permission"] = ["COVID19_FULL"]
        test_event = json.dumps(test_event)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION):
            main(test_event)

        expected_kinesis_data = {"diagnostics": "No permissions for operation"}

        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        test_cases = [
            ("CREATE no permissions", 0, expected_kinesis_data, False),
            ("UPDATE no permissions", 1, expected_kinesis_data, False),
            ("DELETE no permissions", 2, expected_kinesis_data, False),
        ]

        self.make_assertions(test_cases)

    def test_e2e_partial_permissions(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier has partial
        permissions.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE_AND_DELETE)
        event = deepcopy(TEST_EVENT_DUMPED)
        test_event = json.loads(event)
        test_event["permission"] = ["FLU_CREATE"]
        test_event = json.dumps(test_event)
        with patch("process_row.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION):
            main(test_event)

        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        test_cases = [
            ("CREATE create permission only", 0, {"operation_requested": "CREATE"}, True),
            ("UPDATE create permission only", 1, {"diagnostics": "No permissions for operation"}, False),
            ("DELETE create permission only", 2, {"diagnostics": "No permissions for operation"}, False),
        ]

        self.make_assertions(test_cases)

    def test_e2e_invalid_data(self):
        """Tests that file containing CREATEis successfully processed when there is invalid data."""
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW.replace(TEST_DATE, "NOT_A_DATE"))

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION):
            main(TEST_EVENT_DUMPED)

        expected_kinesis_data = {"diagnostics": "Unsupported file type received as an attachment"}
        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        self.make_assertions([("CREATE invalid data", 0, expected_kinesis_data, False)])

    def test_e2e_imms_id_not_found(self):
        """
        Tests that file containing UPDATE and DELETE is successfully processed when the imms id is not found by the API.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_UPDATE_AND_DELETE)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=({"total": 0}, 404)):
            main(TEST_EVENT_DUMPED)

        expected_kinesis_data = {"diagnostics": "Unsupported file type received as an attachment"}
        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        test_cases = [
            ("UPDATE imms id not found", 0, expected_kinesis_data, False),
            ("DELETE imms id not found", 1, expected_kinesis_data, False),
        ]

        self.make_assertions(test_cases)

    def test_e2e_no_imms_id_in_api_response(self):
        """
        Tests that file containing UPDATE and DELETE is successfully processed when API response doesn't contain
        the imms id.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_UPDATE_AND_DELETE)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITHOUT_ID_AND_VERSION):
            main(TEST_EVENT_DUMPED)

        expected_kinesis_data = {"diagnostics": "Unable to obtain imms_id"}
        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        test_cases = [
            ("UPDATE imms no id in API response", 0, expected_kinesis_data, False),
            ("DELETE imms no id in API response", 1, expected_kinesis_data, False),
        ]

        self.make_assertions(test_cases)

    def test_e2e_no_version_in_api_response(self):
        """
        Tests that file containing UPDATE and DELETE is successfully processed when the API response doesn't contain
        the version.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_UPDATE_AND_DELETE)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITHOUT_VERSION):
            main(TEST_EVENT_DUMPED)

        expected_kinesis_data_for_delete = {"operation_requested": "DELETE", "imms_id": TEST_ID}
        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        test_cases = [
            ("UPDATE imms no version in API response", 0, {"diagnostics": "Unable to obtain version"}, False),
            ("DELETE imms no version in API response", 1, expected_kinesis_data_for_delete, True),
        ]

        self.make_assertions(test_cases)

    def test_e2e_no_unique_id(self):
        """Tests that file containing CREATE is successfully processed when the UNIQUE_ID field is empty."""
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW.replace(TEST_UNIQUE_ID, ""))

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION):
            main(TEST_EVENT_DUMPED)

        expected_kinesis_data = {"diagnostics": "Unsupported file type received as an attachment"}
        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        self.make_assertions([("CREATE no unique id", 0, expected_kinesis_data, False)])

    def test_e2e_kinesis_failed(self):
        """
        Tests that, for a file with valid content and supplier with full permissions, when the kinesis send fails, the
        ack file is created and documents an error.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        # Delete the kinesis stream, to cause kinesis send to fail
        kinesis_client.delete_stream(StreamName=STREAM_NAME, EnforceConsumerDeletion=True)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION):
            main(TEST_EVENT_DUMPED)

        self.assertIn("fatal-error", self.get_ack_file_content())


if __name__ == "__main__":
    unittest.main()
