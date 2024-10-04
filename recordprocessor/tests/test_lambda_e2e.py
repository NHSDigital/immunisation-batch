"E2e tests for recordprocessor"

import unittest
import json
from unittest.mock import patch
from boto3 import client as boto3_client
from moto import mock_s3, mock_kinesis
from src.batch_processing import main
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    CONFIG_BUCKET_NAME,
    AWS_REGION,
    VALID_FILE_CONTENT,
    API_RESPONSE_WITH_ID_AND_VERSION,
    STREAM_NAME,
    TEST_ACK_FILE_KEY,
    TEST_EVENT,
    TEST_FILE_KEY,
    MOCK_ENVIRONMENT_DICT,
    MOCK_PERMISSIONS,
    PERMISSIONS_FILE_KEY,
)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
class TestRecordProcessor(unittest.TestCase):
    """E2e tests for RecordProcessor"""

    @staticmethod
    def setup_s3_buckets_and_upload_file(file_content):
        """
        Sets up the source, destination and config buckets. Uploads a test file with the specified content to
        the source bucket. Uploads the permissions config to the config bucket. Returns the S3 client.
        """
        s3_client = boto3_client("s3", region_name=AWS_REGION)

        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME, CONFIG_BUCKET_NAME]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})

        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=file_content)
        s3_client.put_object(Bucket=CONFIG_BUCKET_NAME, Key=PERMISSIONS_FILE_KEY, Body=json.dumps(MOCK_PERMISSIONS))

        return s3_client

    @staticmethod
    def setup_kinesis():
        """Sets up the kinesis stream. Obtains a shard iterator. Returns the kinesis client and shard iterator"""
        kinesis_client = boto3_client("kinesis", region_name=AWS_REGION)
        kinesis_client.create_stream(StreamName=STREAM_NAME, ShardCount=1)

        # Obtain the first shard
        response = kinesis_client.describe_stream(StreamName=STREAM_NAME)
        shards = response["StreamDescription"]["Shards"]
        shard_id = shards[0]["ShardId"]

        # Get a shard iterator (using iterator type "TRIM_HORIZON" to read from the beginning)
        shard_iterator = kinesis_client.get_shard_iterator(
            StreamName=STREAM_NAME, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
        )["ShardIterator"]

        return kinesis_client, shard_iterator

    @staticmethod
    def get_ack_file_content(s3_client):
        """Downloads the ack file, decodes its content and returns the content"""
        response = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_ACK_FILE_KEY)
        return response["Body"].read().decode("utf-8")

    @mock_s3
    @mock_kinesis
    def test_e2e_happy_path(self):
        """
        Tests that, for a file with valid content and supplier with full permissions, the ack file is successfully
        created and a message sent to kinesis.
        """

        s3_client = self.setup_s3_buckets_and_upload_file(VALID_FILE_CONTENT)
        kinesis_client, shard_iterator = self.setup_kinesis()

        with patch("src.batch_processing.ImmunizationApi.get_imms_id", return_value=API_RESPONSE_WITH_ID_AND_VERSION):
            main(TEST_EVENT)

        self.assertIn("ok", self.get_ack_file_content(s3_client))

        kinesis_records = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=10)["Records"]
        self.assertIsNotNone(kinesis_records[0]["Data"])  # The message for first row
        self.assertEqual(kinesis_records[0]["PartitionKey"], "EMIS")
        self.assertEqual(kinesis_records[0]["SequenceNumber"], "1")

    # TODO: Reinstate all tests in this file

    # @patch("batch_processing.convert_to_fhir_json")
    # def test_e2e_processing_invalid_data(self, mock_convert_json):
    #     mock_convert_json.return_value = None, False
    #     self.execute_test(
    #         expected_ack_content="fatal-error",
    #         fetch_file_content=Constants.invalid_file_content,
    #         get_imms_id_response=self.response,
    #         test_event_filename="{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
    #         kinesis=True,
    #     )

    # def test_e2e_processing_imms_id_missing(self):
    #     response = {"total": 0}, 404
    #     self.execute_test(
    #         expected_ack_content="fatal-error",
    #         fetch_file_content=Constants.string_update_return,
    #         get_imms_id_response=response,
    #         test_event_filename="{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
    #         kinesis=True,
    #     )

    # def test_e2e_successful_conversion_kinesis_failed(self):
    #     self.execute_test(
    #         expected_ack_content="fatal-error",
    #         fetch_file_content=Constants.string_return,
    #         get_imms_id_response=self.response,
    #         test_event_filename="{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv",
    #         kinesis=False,
    #     )

    # TODO: REPLACE THIS TEST WITH NEW PERMISSIONS LOGIC
    # @mock_s3
    # def test_validate_full_permissions_end_to_end(self):
    #     config_bucket_name = "test-bucket"
    #     self.s3_client.create_bucket(
    #         Bucket=config_bucket_name,
    #         CreateBucketConfiguration={"LocationConstraint": self.region},
    #     )

    #     permissions_data = {"all_permissions": {"DP": ["FLU_FULL"]}}
    #     self.s3_client.put_object(
    #         Bucket=config_bucket_name,
    #         Key="permissions.json",
    #         Body=json.dumps(permissions_data),
    #     )

    #     def mock_get_permissions_config_json_from_s3(config_bucket_name):
    #         return permissions_data

    #     with patch("batch_processing.get_permissions_config_json_from_s3", mock_get_permissions_config_json_from_s3):
    #         result = validate_full_permissions(config_bucket_name, "DP", "FLU")
    #         self.assertTrue(result)

    #         permissions_data["all_permissions"]["DP"] = ["FLU_CREATE"]
    #         result = validate_full_permissions(config_bucket_name, "DP", "FLU")
    #         self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
