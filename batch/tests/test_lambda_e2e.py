import boto3
import unittest

# import json
from unittest.mock import patch, MagicMock
from moto import mock_s3, mock_sqs
from src.constants import Constant


from router_lambda_function import (
    lambda_handler,
    validate_action_flag_permissions,
)


class TestRouterLambdaFunctionEndToEnd(unittest.TestCase):

    @patch("router_lambda_function.s3_client")
    @patch("router_lambda_function.sqs_client")
    @patch("router_lambda_function.validate_csv_column_count")
    @patch("router_lambda_function.get_supplier_permissions")
    def test_lambda_handler(
        self,
        mock_get_supplier_permissions,
        mock_validate_csv_column_count,
        mock_sqs_client,
        mock_s3_client,
    ):

        # Mock permissions configuration
        mock_get_supplier_permissions.return_value = {
            "all_permissions": {"EMIS": ["FLU_FULL"]}
        }

        # Mock an S3 event
        event = {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "eu-west-2",
                    "eventTime": "2024-07-09T12:00:00Z",
                    "eventName": "ObjectCreated:Put",
                    "userIdentity": {"principalId": "AWS:123456789012:user/Admin"},
                    "requestParameters": {"sourceIPAddress": "127.0.0.1"},
                    "responseElements": {
                        "x-amz-request-id": "EXAMPLE123456789",
                        "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH",
                    },
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "configurationId": "testConfigRule",
                        "bucket": {
                            "name": "test-bucket",
                            "ownerIdentity": {"principalId": "EXAMPLE"},
                            "arn": "arn:aws:s3:::example-bucket",
                        },
                        "object": {
                            "key": "FLU_Vaccinations_v5_YGM41_20240708T12130100.csv",
                            "size": 1024,
                            "eTag": "5",
                            "sequencer": "0A1B2C3D4E5F678901",
                        },
                    },
                }
            ]
        }

        # Mock S3 client upload_fileobj
        mock_s3_client.upload_fileobj = MagicMock()

        # Mock SQS client send_message
        mock_sqs_client.send_message = MagicMock()

        # Mock validate_csv_column_count to return valid response
        mock_validate_csv_column_count.return_value = (True, [])

        # Mock initial_file_validation function
        with patch(
            "router_lambda_function.initial_file_validation", return_value=(True, False)
        ) as mock_validation:
            # Invoke Lambda function
            lambda_handler(event, None)

            # Assertions
            mock_validation.assert_called_once_with(
                "FLU_Vaccinations_v5_YGM41_20240708T12130100.csv", "test-bucket"
            )
            mock_s3_client.upload_fileobj.assert_called_once()
            mock_sqs_client.send_message.assert_called_once()


class TestLambdaHandler(unittest.TestCase):

    # @mock_s3
    # @mock_sqs
    # @patch("router_lambda_function.get_supplier_permissions")
    # def test_lambda_handler(self, mock_get_supplier_permissions):
    #     """Tests lambda function end to end"""

    #     # Set up S3
    #     s3_client = boto3.client("s3", region_name="eu-west-2")
    #     source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
    #     destination_bucket_name = (
    #         "immunisation-batch-internal-dev-batch-data-destination"
    #     )

    #     # Create source and destination buckets
    #     s3_client.create_bucket(
    #         Bucket=source_bucket_name,
    #         CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
    #     )
    #     s3_client.create_bucket(
    #         Bucket=destination_bucket_name,
    #         CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
    #     )

    #     print(f"Source Bucket: {source_bucket_name}")
    #     print(f"Destination Bucket: {destination_bucket_name}")
    #     print(f"Region: {s3_client.meta.region_name}")
    #     # check if bucket exists
    #     response = s3_client.list_buckets()
    #     buckets = [bucket["Name"] for bucket in response["Buckets"]]
    #     print(f"allBuckets: {buckets}")
    #     self.assertIn(
    #         source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
    #     )
    #     self.assertIn(
    #         destination_bucket_name,
    #         buckets,
    #         f"Bucket {destination_bucket_name} not found",
    #     )

    #     # Upload a test file
    #     test_file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
    #     test_file_content = "example content"
    #     s3_client.put_object(
    #         Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content
    #     )

    #     # upload test permissions file
    #     sample_permissions_config = {"all_permissions": {"EMIS": ["FLU_FULL"]}}
    #     test_permissions_file_key = "permissions_config.json"
    #     s3_client.put_object(
    #         Bucket=source_bucket_name,
    #         Key=test_permissions_file_key,
    #         Body=json.dumps(sample_permissions_config),
    #     )

    #     # Mock permissions configuration
    #     mock_get_supplier_permissions.return_value = ["FLU_FULL"]

    #     # Set up SQS
    #     sqs_client = boto3.client("sqs", region_name="eu-west-2")
    #     queue_url = sqs_client.create_queue(
    #         QueueName="imms-batch-internal-dev-EMIS-metadata-queue.fifo",
    #         Attributes={"FIFOQueue": "true", "ContentBasedDeduplication": "true"},
    #     )["QueueUrl"]

    #     # Prepare the event
    #     event = {
    #         "Records": [
    #             {
    #                 "s3": {
    #                     "bucket": {"name": source_bucket_name},
    #                     "object": {"key": test_file_key},
    #                 }
    #             }
    #         ]
    #     }

    #     # Mock the validate_csv_column_count function
    #     with patch(
    #         "router_lambda_function.validate_csv_column_count",
    #         return_value=(True, False),
    #     ):
    #         # Call the lambda_handler function
    #         response = lambda_handler(event, None)

    #     # Assertions
    #     self.assertEqual(response["statusCode"], 200)

    #     # Check if the acknowledgment file is created in the S3 bucket
    #     ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_response.csv"
    #     ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
    #     ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
    #     self.assertIn(ack_file_key, ack_file_keys)

    #     # # Check if the message was sent to the SQS queue
    #     messages = sqs_client.receive_message(
    #         QueueUrl=queue_url, WaitTimeSeconds=1, MaxNumberOfMessages=1
    #     )
    #     print(f"RRRdmssge:{messages}")
    #     self.assertIn("Messages", messages)
    #     received_message = json.loads(messages["Messages"][0]["Body"])
    #     # print(f"R2D2:{received_message}")
    #     self.assertEqual(received_message["vaccine_type"], "Flu")
    #     self.assertEqual(received_message["supplier"], "EMIS")
    #     self.assertEqual(received_message["timestamp"], "20240708T12130100")
    #     self.assertEqual(
    #         received_message["filename"],
    #         "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv",
    #     )

    @mock_s3
    @mock_sqs
    @patch("router_lambda_function.send_to_supplier_queue")
    @patch("router_lambda_function.get_supplier_permissions")
    def test_lambda_invalid(
        self, mock_send_to_supplier_queue, mock_get_supplier_permissions
    ):
        """tests SQS queue is not called when file validation failed"""
        # Mock permissions configuration
        mock_get_supplier_permissions.return_value = {
            "all_permissions": {"EMIS": ["FLU_FULL"]}
        }

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")
        source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
        destination_bucket_name = (
            "immunisation-batch-internal-dev-batch-data-destination"
        )

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=destination_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        self.assertIn(
            source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
        )
        self.assertIn(
            destination_bucket_name,
            buckets,
            f"Bucket {destination_bucket_name} not found",
        )
        # Upload a test file
        test_file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        test_file_content = "example content"
        s3_client.put_object(
            Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content
        )

        # Prepare the event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": source_bucket_name},
                        "object": {"key": test_file_key},
                    }
                }
            ]
        }

        # Call the lambda_handler function
        lambda_handler(event, None)
        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch("router_lambda_function.send_to_supplier_queue")
    def test_lambda_invalid_csv_header(self, mock_send_to_supplier_queue):
        """tests SQS queue is not called when CSV headers are invalid"""

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")
        source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
        destination_bucket_name = (
            "immunisation-batch-internal-dev-batch-data-destination"
        )

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=destination_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        self.assertIn(
            source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
        )
        self.assertIn(
            destination_bucket_name,
            buckets,
            f"Bucket {destination_bucket_name} not found",
        )
        # Upload a test file with an invalid header
        test_file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        s3_client.put_object(
            Bucket=source_bucket_name,
            Key=test_file_key,
            Body=Constant.invalid_csv_content,
        )

        # Prepare the event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": source_bucket_name},
                        "object": {"key": test_file_key},
                    }
                }
            ]
        }

        # Call the lambda_handler function
        lambda_handler(event, None)

        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()

        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

        # Validate the content of the ack file to ensure it reports an error due to invalid headers
        ack_file_obj = s3_client.get_object(
            Bucket=destination_bucket_name, Key=ack_file_key
        )
        ack_file_content = ack_file_obj["Body"].read().decode("utf-8")
        self.assertIn("error", ack_file_content)
        self.assertIn(
            "Unsupported file type received as an attachment", ack_file_content
        )

    @mock_s3
    @mock_sqs
    @patch("router_lambda_function.send_to_supplier_queue")
    def test_lambda_invalid_columns_header_count(self, mock_send_to_supplier_queue):
        """tests SQS queue is not called when file validation failed"""

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")
        source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
        destination_bucket_name = (
            "immunisation-batch-internal-dev-batch-data-destination"
        )

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=destination_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        self.assertIn(
            source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
        )
        self.assertIn(
            destination_bucket_name,
            buckets,
            f"Bucket {destination_bucket_name} not found",
        )
        # Upload a test file
        test_file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        test_file_content = "example content"
        s3_client.put_object(
            Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content
        )

        # Prepare the event.
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": source_bucket_name},
                        "object": {"key": test_file_key},
                    }
                }
            ]
        }

        # Call the lambda_handler function.
        lambda_handler(event, None)
        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket.
        ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch("router_lambda_function.send_to_supplier_queue")
    def test_lambda_invalid_vaccine_type(self, mock_send_to_supplier_queue):
        """tests SQS queue is not called when file validation failed"""

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")
        source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
        destination_bucket_name = (
            "immunisation-batch-internal-dev-batch-data-destination"
        )

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=destination_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]

        self.assertIn(
            source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
        )
        self.assertIn(
            destination_bucket_name,
            buckets,
            f"Bucket {destination_bucket_name} not found",
        )
        # Upload a test file
        test_file_key = "Invalid_Vaccinations_v5_YGM41_20240708T12130100.csv"
        test_file_content = "example content"
        s3_client.put_object(
            Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content
        )

        # Prepare the event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": source_bucket_name},
                        "object": {"key": test_file_key},
                    }
                }
            ]
        }

        # Call the lambda_handler function
        lambda_handler(event, None)
        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = (
            "ack/Invalid_Vaccinations_v5_YGM41_20240708T12130100_response.csv"
        )
        ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch("router_lambda_function.send_to_supplier_queue")
    def test_lambda_invalid_vaccination(self, mock_send_to_supplier_queue):
        """tests SQS queue is not called when file validation failed"""

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")
        source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
        destination_bucket_name = (
            "immunisation-batch-internal-dev-batch-data-destination"
        )

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=destination_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        self.assertIn(
            source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
        )
        self.assertIn(
            destination_bucket_name,
            buckets,
            f"Bucket {destination_bucket_name} not found",
        )
        # Upload a test file
        test_file_key = "Flu_Vaccination_v5_YGM41_20240708T12130100.csv"
        test_file_content = "example content"
        s3_client.put_object(
            Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content
        )

        # Prepare the event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": source_bucket_name},
                        "object": {"key": test_file_key},
                    }
                }
            ]
        }

        # Call the lambda_handler function
        lambda_handler(event, None)
        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccination_v5_YGM41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch("router_lambda_function.send_to_supplier_queue")
    def test_lambda_invalid_version(self, mock_send_to_supplier_queue):
        """tests SQS queue is not called when file validation failed"""

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")
        source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
        destination_bucket_name = (
            "immunisation-batch-internal-dev-batch-data-destination"
        )

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=destination_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        self.assertIn(
            source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
        )
        self.assertIn(
            destination_bucket_name,
            buckets,
            f"Bucket {destination_bucket_name} not found",
        )
        # Upload a test file
        test_file_key = "Flu_Vaccinations_v4_YGM41_20240708T12130100.csv"
        test_file_content = "example content"
        s3_client.put_object(
            Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content
        )

        # Prepare the event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": source_bucket_name},
                        "object": {"key": test_file_key},
                    }
                }
            ]
        }

        # Call the lambda_handler function
        lambda_handler(event, None)
        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccinations_v4_YGM41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch("router_lambda_function.send_to_supplier_queue")
    def test_lambda_invalid_odscode(self, mock_send_to_supplier_queue):
        """tests SQS queue is not called when file validation failed"""

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")
        source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
        destination_bucket_name = (
            "immunisation-batch-internal-dev-batch-data-destination"
        )

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=destination_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]

        self.assertIn(
            source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
        )
        self.assertIn(
            destination_bucket_name,
            buckets,
            f"Bucket {destination_bucket_name} not found",
        )
        # Upload a test file
        test_file_key = "Flu_Vaccinations_v5_YGMs41_20240708T12130100.csv"
        test_file_content = "example content"
        s3_client.put_object(
            Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content
        )

        # Prepare the event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": source_bucket_name},
                        "object": {"key": test_file_key},
                    }
                }
            ]
        }

        lambda_handler(event, None)

        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccinations_v5_YGMs41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch("router_lambda_function.send_to_supplier_queue")
    def test_lambda_invalid_datetime(self, mock_send_to_supplier_queue):
        """tests SQS queue is not called when file validation failed"""

        # Set up S3
        s3_client = boto3.client("s3", region_name="eu-west-2")
        source_bucket_name = "immunisation-batch-internal-dev-batch-data-source"
        destination_bucket_name = (
            "immunisation-batch-internal-dev-batch-data-destination"
        )

        # Create source and destination buckets
        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        s3_client.create_bucket(
            Bucket=destination_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        self.assertIn(
            source_bucket_name, buckets, f"Bucket {source_bucket_name} not found"
        )
        self.assertIn(
            destination_bucket_name,
            buckets,
            f"Bucket {destination_bucket_name} not found",
        )
        # Upload a test file
        test_file_key = "Flu_Vaccinations_v5_YGM41_20240732T12130100.csv"
        test_file_content = "example content"
        s3_client.put_object(
            Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content
        )

        # Prepare the event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": source_bucket_name},
                        "object": {"key": test_file_key},
                    }
                }
            ]
        }

        lambda_handler(event, None)

        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240732T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(Bucket=destination_bucket_name)
        ack_file_keys = [obj["Key"] for obj in ack_files.get("Contents", [])]
        self.assertIn(ack_file_key, ack_file_keys)


class TestValidateActionFlagPermissions(unittest.TestCase):

    @mock_s3
    def test_validate_action_flag_permissions_end_to_end(self):
        # Define test parameters
        s3_client = boto3.client("s3", region_name="eu-west-2")
        csv_data = "ACTION_FLAG\nnew\nupdate\ndelete\n"
        source_bucket_name = "test-bucket"
        file_key = "Flu_Vaccinations_v5_YYY78_20240708T12130100.csv"
        supplier = "supplier_123"
        vaccine_type = "FLU"

        s3_client.create_bucket(
            Bucket=source_bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )

        s3_client.put_object(
            Bucket=source_bucket_name,
            Key="Flu_Vaccinations_v5_YYY78_20240708T12130100.csv",
            Body=csv_data,
        )
        s3_client.put_object(
            Bucket=source_bucket_name,
            Key="Flu_Vaccinations_v5_YYY78_20240708T12130100.csv",
            Body=csv_data,
        )

        # Mock the permissions configuration
        Constant.action_flag_mapping = {
            "NEW": "CREATE",
            "UPDATE": "UPDATE",
            "DELETE": "DELETE",
        }

        # Mock supplier permissions
        def mock_get_supplier_permissions(supplier, source_bucket_name):
            return ["FLU_CREATE", "FLU_UPDATE", "COVID_FULL"]

        original_get_supplier_permissions = (
            validate_action_flag_permissions.__globals__["get_supplier_permissions"]
        )
        validate_action_flag_permissions.__globals__["get_supplier_permissions"] = (
            mock_get_supplier_permissions
        )

        try:
            # Call the function
            result = validate_action_flag_permissions(
                source_bucket_name, file_key, supplier, vaccine_type
            )
            print(f"RESULT RESULT: {result}")
            # Check the result
            self.assertTrue(result)
        finally:
            validate_action_flag_permissions.__globals__["get_supplier_permissions"] = (
                original_get_supplier_permissions
            )


if __name__ == "__main__":
    unittest.main()
