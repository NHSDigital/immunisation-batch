"E2e tests for recordprocessor"

import unittest
import json
from decimal import Decimal
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from copy import deepcopy
from moto import mock_s3, mock_kinesis
from boto3 import client as boto3_client
from src.batch_processing import main
from src.constants import Diagnostics
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    CONFIG_BUCKET_NAME,
    PERMISSIONS_FILE_KEY,
    AWS_REGION,
    VALID_FILE_CONTENT_WITH_NEW,
    VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE,
    VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE_AND_DELETE,
    STREAM_NAME,
    TEST_ACK_FILE_KEY,
    TEST_EVENT_DUMPED,
    TEST_FILE_KEY,
    TEST_SUPPLIER,
    TEST_FILE_ID,
    MOCK_ENVIRONMENT_DICT,
    MOCK_PERMISSIONS,
    all_fields,
    mandatory_fields_only,
    critical_fields_only,
    all_fields_fhir_imms_resource,
    mandatory_fields_only_fhir_imms_resource,
    critical_fields_only_fhir_imms_resource,
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

        for test_name, index, expected_kinesis_data, expect_success in test_cases:
            with self.subTest(test_name):

                kinesis_record = kinesis_records[index]
                self.assertEqual(kinesis_record["PartitionKey"], TEST_SUPPLIER)
                self.assertEqual(kinesis_record["SequenceNumber"], f"{index+1}")

                # Ensure that arrival times are sequential
                approximate_arrival_timestamp = kinesis_record["ApproximateArrivalTimestamp"]
                self.assertGreater(approximate_arrival_timestamp, previous_approximate_arrival_time_stamp)
                previous_approximate_arrival_time_stamp = approximate_arrival_timestamp

                kinesis_data = json.loads(kinesis_record["Data"].decode("utf-8"), parse_float=Decimal)
                expected_kinesis_data = {
                    "row_id": f"{TEST_FILE_ID}#{index+1}",
                    "file_key": TEST_FILE_KEY,
                    "supplier": TEST_SUPPLIER,
                    **expected_kinesis_data,
                }
                if expect_success:
                    # Some tests ignore the fhir_json value, so we only need to check that the key is present.
                    if "fhir_json" not in expected_kinesis_data:
                        key_to_ignore = "fhir_json"
                        self.assertIn(key_to_ignore, kinesis_data)
                        kinesis_data.pop(key_to_ignore)
                    self.assertEqual(kinesis_data, expected_kinesis_data)
                    self.assertIn(f"{TEST_FILE_ID}#{index+1}|OK", ack_file_content)
                else:
                    self.assertEqual(kinesis_data, expected_kinesis_data)
                    self.assertIn(f"{TEST_FILE_ID}#{index+1}|Fatal", ack_file_content)

    def test_e2e_success(self):
        """
        Tests that file containing CREATE, UPDATE and DELETE is successfully processed when the supplier has
        full permissions.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE_AND_DELETE)

        main(TEST_EVENT_DUMPED)

        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        test_cases = [
            ("CREATE success", 0, {"operation_requested": "CREATE"}, True),
            ("UPDATE success", 1, {"operation_requested": "UPDATE"}, True),
            ("DELETE success", 2, {"operation_requested": "DELETE"}, True),
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

        main(test_event)
        expected_kinesis_data = {"diagnostics": Diagnostics.NO_PERMISSIONS}

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
        test_event["permission"] = ["RSV_CREATE"]
        test_event = json.dumps(test_event)

        main(test_event)
        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        test_cases = [
            ("CREATE create permission only", 0, {"operation_requested": "CREATE"}, True),
            ("UPDATE create permission only", 1, {"diagnostics": Diagnostics.NO_PERMISSIONS}, False),
            ("DELETE create permission only", 2, {"diagnostics": Diagnostics.NO_PERMISSIONS}, False),
        ]

        self.make_assertions(test_cases)

    def test_e2e_no_action_flag(self):
        """Tests that file containing CREATE is successfully processed when the UNIQUE_ID field is empty."""
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW.replace("new", ""))

        main(TEST_EVENT_DUMPED)

        expected_kinesis_data = {"diagnostics": Diagnostics.INVALID_ACTION_FLAG}
        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        self.make_assertions([("CREATE no action_flag", 0, expected_kinesis_data, False)])

    def test_e2e_invalid_action_flag(self):
        """Tests that file containing CREATE is successfully processed when the UNIQUE_ID field is empty."""
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW.replace("new", "invalid"))

        main(TEST_EVENT_DUMPED)

        expected_kinesis_data = {"diagnostics": Diagnostics.INVALID_ACTION_FLAG}
        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data_ignoring_fhir_json, expect_success)
        self.make_assertions([("CREATE invalid action_flag", 0, expected_kinesis_data, False)])

    def test_e2e_differing_amounts_of_data(self):
        """Tests that file containing rows with differing amounts of data present is processed as expected"""
        # Create file content with different amounts of data present in each row
        headers = "|".join(all_fields.keys())
        all_fields_values = "|".join(f'"{v}"' for v in all_fields.values())
        mandatory_fields_only_values = "|".join(f'"{v}"' for v in mandatory_fields_only.values())
        critical_fields_only_values = "|".join(f'"{v}"' for v in critical_fields_only.values())
        file_content = f"{headers}\n{all_fields_values}\n{mandatory_fields_only_values}\n{critical_fields_only_values}"
        self.upload_files(file_content)

        main(TEST_EVENT_DUMPED)

        all_fields_row_expected_kinesis_data = {
            "operation_requested": "UPDATE",
            "fhir_json": all_fields_fhir_imms_resource,
        }

        mandatory_fields_only_row_expected_kinesis_data = {
            "operation_requested": "UPDATE",
            "fhir_json": mandatory_fields_only_fhir_imms_resource,
        }

        critical_fields_only_row_expected_kinesis_data = {
            "operation_requested": "CREATE",
            "fhir_json": critical_fields_only_fhir_imms_resource,
        }

        # Test case tuples are stuctured as (test_name, index, expected_kinesis_data, expect_success)
        test_cases = [
            ("All fields", 0, all_fields_row_expected_kinesis_data, True),
            ("Mandatory fields only", 1, mandatory_fields_only_row_expected_kinesis_data, True),
            ("Critical fields only", 2, critical_fields_only_row_expected_kinesis_data, True),
        ]
        self.make_assertions(test_cases)

    def test_e2e_kinesis_failed(self):
        """
        Tests that, for a file with valid content and supplier with full permissions, when the kinesis send fails, the
        ack file is created and documents an error.
        """
        self.upload_files(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        # Delete the kinesis stream, to cause kinesis send to fail
        kinesis_client.delete_stream(StreamName=STREAM_NAME, EnforceConsumerDeletion=True)

        main(TEST_EVENT_DUMPED)

        self.assertIn("Fatal", self.get_ack_file_content())


if __name__ == "__main__":
    unittest.main()
