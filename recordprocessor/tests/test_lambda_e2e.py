"E2e tests for recordprocessor"

import unittest
from unittest.mock import patch
from copy import deepcopy
from moto import mock_s3, mock_kinesis
from boto3 import client as boto3_client
from src.batch_processing import main
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    AWS_REGION,
    VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE,
    API_RESPONSE_WITH_ID_AND_VERSION,
    STREAM_NAME,
    TEST_ACK_FILE_KEY,
    TEST_EVENT,
    TEST_FILE_KEY,
    MOCK_ENVIRONMENT_DICT,
    MOCK_PERMISSIONS,
)

s3_client = boto3_client("s3", region_name=AWS_REGION)
kinesis_client = boto3_client("kinesis", region_name=AWS_REGION)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_kinesis
class TestRecordProcessor(unittest.TestCase):
    """E2e tests for RecordProcessor"""

    def setUp(self) -> None:
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})

    def tearDown(self) -> None:
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            s3_client.delete_bucket(Bucket=bucket_name)

    @staticmethod
    def upload_source_file(file_content):
        """
        Uploads a test file with the TEST_FILE_KEY (Flu EMIS file) the given file content to the source bucket
        """
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=file_content)

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

    @staticmethod
    def get_ack_file_content():
        """Downloads the ack file, decodes its content and returns the content"""
        response = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_ACK_FILE_KEY)
        return response["Body"].read().decode("utf-8")

    def test_e2e_happy_path(self):
        """
        Tests that, for a file with valid content and supplier with full permissions, the ack file is successfully
        created and a message sent to kinesis.
        """
        self.upload_source_file(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        shard_iterator = self.setup_kinesis()

        with patch(
            "src.batch_processing.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION
        ), patch("src.batch_processing.get_permissions_config_json_from_s3", return_value=MOCK_PERMISSIONS):
            main(TEST_EVENT)

        self.assertIn("ok", self.get_ack_file_content())

        kinesis_records = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)["Records"]
        self.assertIsNotNone(kinesis_records[0]["Data"])  # The message for first row
        self.assertEqual(kinesis_records[0]["PartitionKey"], "EMIS")
        self.assertEqual(kinesis_records[0]["SequenceNumber"], "1")

    def test_e2e_no_permissions(self):
        """
        Tests that, for a file with valid content and supplier with no permissions, the ack file is successfully
        created and documents an error for each line and a message sent to kinesis.
        """
        permissions = deepcopy(MOCK_PERMISSIONS)
        permissions["all_permissions"]["EMIS"] = []
        self.upload_source_file(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        shard_iterator = self.setup_kinesis()

        with patch(
            "src.batch_processing.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION
        ), patch("src.batch_processing.get_permissions_config_json_from_s3", return_value=permissions):
            main(TEST_EVENT)

        ack_file = self.get_ack_file_content()
        self.assertIn("123456#1|fatal-error", ack_file)
        self.assertIn("123456#2|fatal-error", ack_file)

        kinesis_records = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)["Records"]
        self.assertIsNotNone(kinesis_records[0]["Data"])  # The message for first row
        self.assertEqual(kinesis_records[0]["PartitionKey"], "EMIS")
        self.assertEqual(kinesis_records[0]["SequenceNumber"], "1")

    def test_e2e_one_permissions(self):
        """
        Tests that, for a file with valid content and supplier with one permission, the ack file is successfully
        created and documents 'ok' for the permitted line and 'fatal-error' for the non-permitted line and a message is
        sent to kinesis.
        """
        permissions = deepcopy(MOCK_PERMISSIONS)
        permissions["all_permissions"]["EMIS"] = ["FLU_NEW"]
        self.upload_source_file(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        shard_iterator = self.setup_kinesis()

        with patch(
            "src.batch_processing.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION
        ), patch("src.batch_processing.get_permissions_config_json_from_s3", return_value=permissions):
            main(TEST_EVENT)

        ack_file = self.get_ack_file_content()
        self.assertIn("123456#1|ok", ack_file)
        self.assertIn("123456#2|fatal-error", ack_file)
        print(ack_file)

        kinesis_records = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)["Records"]
        self.assertIsNotNone(kinesis_records[0]["Data"])  # The message for first row
        self.assertEqual(kinesis_records[0]["PartitionKey"], "EMIS")
        self.assertEqual(kinesis_records[0]["SequenceNumber"], "1")

    def test_e2e_invalid_data(self):
        """
        Tests that, for a file with invalid content and supplier with full permissions, the ack file is successfully
        created and documents an error and a message is sent to kinesis.
        """
        self.upload_source_file(
            VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE.replace('"0001_RSV_v5_RUN_2_CDFDPS-742_valid_dose_1"', "")
        )
        shard_iterator = self.setup_kinesis()

        with patch(
            "src.batch_processing.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION
        ), patch("src.batch_processing.get_permissions_config_json_from_s3", return_value=MOCK_PERMISSIONS):
            main(TEST_EVENT)

        self.assertIn("fatal-error", self.get_ack_file_content())

        kinesis_records = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)["Records"]
        self.assertIsNotNone(kinesis_records[0]["Data"])  # The message for first row
        self.assertEqual(kinesis_records[0]["PartitionKey"], "EMIS")
        self.assertEqual(kinesis_records[0]["SequenceNumber"], "1")

    def test_e2e_imms_id_not_found(self):
        """
        Tests that when the imms id can't be found for an update, the ack file is successfully
        created and documents an error and a message is sent to kinesis.
        """
        self.upload_source_file(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        shard_iterator = self.setup_kinesis()

        with patch("src.batch_processing.ImmunizationApi.get_imms_id", return_value=({"total": 0}, 404)), patch(
            "src.batch_processing.get_permissions_config_json_from_s3", return_value=MOCK_PERMISSIONS
        ):
            main(TEST_EVENT)

        self.assertIn("fatal-error", self.get_ack_file_content())

        kinesis_records = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)["Records"]
        self.assertIsNotNone(kinesis_records[0]["Data"])  # The message for first row
        self.assertEqual(kinesis_records[0]["PartitionKey"], "EMIS")
        self.assertEqual(kinesis_records[0]["SequenceNumber"], "1")

    def test_e2e_kinesis_failed(self):
        """
        Tests that, for a file with valid content and supplier with full permissions, when the kinesis send fails, the
        ack file created and documents an erro and a message in not sent to kinesis.
        """

        self.upload_source_file(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        shard_iterator = self.setup_kinesis(stream_name="INVALID_STREAM")

        with patch(
            "src.batch_processing.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION
        ), patch("src.batch_processing.get_permissions_config_json_from_s3", return_value=MOCK_PERMISSIONS):
            main(TEST_EVENT)

        self.assertIn("fatal-error", self.get_ack_file_content())

        kinesis_records = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)["Records"]
        self.assertEqual(kinesis_records, [])


if __name__ == "__main__":
    unittest.main()
