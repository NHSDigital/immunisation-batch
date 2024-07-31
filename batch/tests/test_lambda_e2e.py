
import unittest
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_s3, mock_sqs
import json
from src.constants import Constant
from datetime import datetime
# from io import BytesIO
from router_lambda_function import (
    lambda_handler  # Import lambda_handler for end-to-end test
)
from processing_lambda import (process_lambda_handler)


class TestRouterLambdaFunctionEndToEnd(unittest.TestCase):

    @patch('router_lambda_function.s3_client')
    @patch('router_lambda_function.sqs_client')
    @patch('router_lambda_function.validate_csv_column_count')
    def test_lambda_handler(self, mock_validate_csv_column_count, mock_sqs_client, mock_s3_client):
        # Mock S3 event
        event = {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "eu-west-2",
                    "eventTime": "2024-07-09T12:00:00Z",
                    "eventName": "ObjectCreated:Put",
                    "userIdentity": {
                        "principalId": "AWS:123456789012:user/Admin"
                    },
                    "requestParameters": {
                        "sourceIPAddress": "127.0.0.1"
                    },
                    "responseElements": {
                        "x-amz-request-id": "EXAMPLE123456789",
                        "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH"
                    },
                    "s3": {
                        "s3SchemaVersion": "1.0",
                        "configurationId": "testConfigRule",
                        "bucket": {
                            "name": "test-bucket",
                            "ownerIdentity": {
                                "principalId": "EXAMPLE"
                            },
                            "arn": "arn:aws:s3:::example-bucket"
                        },
                        "object": {
                            "key": "FLU_Vaccinations_v5_YGM41_20240708T12130100.csv",
                            "size": 1024,
                            "eTag": "5",
                            "sequencer": "0A1B2C3D4E5F678901"
                        }
                    }
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
        with patch('router_lambda_function.initial_file_validation', return_value=(True, False)) as mock_validation:
            # Invoke Lambda function
            lambda_handler(event, None)

            # Assertions
            mock_validation.assert_called_once_with(
                "FLU_Vaccinations_v5_YGM41_20240708T12130100.csv", "test-bucket"
            )
            mock_s3_client.upload_fileobj.assert_called_once()
            mock_sqs_client.send_message.assert_called_once()


class TestLambdaHandler(unittest.TestCase):

    @mock_s3
    @mock_sqs
    def test_lambda_handler(self):
        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")
        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")

        # Upload a test file
        test_file_key = 'Flu_Vaccinations_v5_YGM41_20240708T12130100.csv'
        test_file_content = "example content"
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content)

        # Set up SQS
        sqs_client = boto3.client('sqs', region_name='eu-west-2')
        queue_url = sqs_client.create_queue(QueueName='EMIS_metadata_queue')['QueueUrl']

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
                    }
                }
            ]
        }

        # Mock the validate_csv_column_count function
        with patch('router_lambda_function.validate_csv_column_count', return_value=(True, False)):
            # Call the lambda_handler function
            response = lambda_handler(event, None)

        # Assertions
        self.assertEqual(response['statusCode'], 200)

        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

        # Check if the message was sent to the SQS queue
        messages = sqs_client.receive_message(QueueUrl=queue_url)
        self.assertIn('Messages', messages)
        received_message = json.loads(messages['Messages'][0]['Body'])
        self.assertEqual(received_message['vaccine_type'], 'Flu')
        self.assertEqual(received_message['supplier'], 'EMIS')
        self.assertEqual(received_message['timestamp'], '20240708T12130100')

    @mock_s3
    @mock_sqs
    @patch('router_lambda_function.send_to_supplier_queue')
    def test_lambda_invalid(self, mock_send_to_supplier_queue):
        '''tests SQS queue is not called when file validation failed'''

        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")
        # Upload a test file
        test_file_key = 'Flu_Vaccinations_v5_YGM41_20240708T12130100.csv'
        test_file_content = "example content"
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content)

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
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
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch('router_lambda_function.send_to_supplier_queue')
    def test_lambda_invalid_csv_header(self, mock_send_to_supplier_queue):
        '''tests SQS queue is not called when CSV headers are invalid'''

        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")
        # Upload a test file with an invalid header
        test_file_key = 'Flu_Vaccinations_v5_YGM41_20240708T12130100.csv'
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=Constant.invalid_csv_content)

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
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
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

        # Validate the content of the ack file to ensure it reports an error due to invalid headers
        ack_file_obj = s3_client.get_object(Bucket=destination_bucket_name, Key=ack_file_key)
        ack_file_content = ack_file_obj['Body'].read().decode('utf-8')
        self.assertIn('error', ack_file_content)
        self.assertIn('Unsupported file type received as an attachment', ack_file_content)

    @mock_s3
    @mock_sqs
    @patch('router_lambda_function.send_to_supplier_queue')
    def test_lambda_invalid_columns_header_count(self, mock_send_to_supplier_queue):
        '''tests SQS queue is not called when file validation failed'''

        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")
        # Upload a test file
        test_file_key = 'Flu_Vaccinations_v5_YGM41_20240708T12130100.csv'
        test_file_content = "example content"
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content)

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
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
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch('router_lambda_function.send_to_supplier_queue')
    def test_lambda_invalid_vaccine_type(self, mock_send_to_supplier_queue):
        '''tests SQS queue is not called when file validation failed'''

        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")
        # Upload a test file
        test_file_key = 'Invalid_Vaccinations_v5_YGM41_20240708T12130100.csv'
        test_file_content = "example content"
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content)

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
                    }
                }
            ]
        }

        # Call the lambda_handler function
        lambda_handler(event, None)
        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Invalid_Vaccinations_v5_YGM41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch('router_lambda_function.send_to_supplier_queue')
    def test_lambda_invalid_vaccination(self, mock_send_to_supplier_queue):
        '''tests SQS queue is not called when file validation failed'''

        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")
        # Upload a test file
        test_file_key = 'Flu_Vaccination_v5_YGM41_20240708T12130100.csv'
        test_file_content = "example content"
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content)

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
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
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch('router_lambda_function.send_to_supplier_queue')
    def test_lambda_invalid_version(self, mock_send_to_supplier_queue):
        '''tests SQS queue is not called when file validation failed'''

        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")
        # Upload a test file
        test_file_key = 'Flu_Vaccinations_v4_YGM41_20240708T12130100.csv'
        test_file_content = "example content"
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content)

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
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
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch('router_lambda_function.send_to_supplier_queue')
    def test_lambda_invalid_odscode(self, mock_send_to_supplier_queue):
        '''tests SQS queue is not called when file validation failed'''

        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")
        # Upload a test file
        test_file_key = 'Flu_Vaccinations_v5_YGMs41_20240708T12130100.csv'
        test_file_content = "example content"
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content)

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
                    }
                }
            ]
        }

        # Call the lambda_handler function
        lambda_handler(event, None)
        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccinations_v5_YGMs41_20240708T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch('router_lambda_function.send_to_supplier_queue')
    def test_lambda_invalid_datetime(self, mock_send_to_supplier_queue):
        '''tests SQS queue is not called when file validation failed'''

        # Set up S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        destination_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'

        # Create source and destination buckets
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=destination_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })

        print(f"Source Bucket: {source_bucket_name}")
        print(f"Destination Bucket: {destination_bucket_name}")
        print(f"Region: {s3_client.meta.region_name}")

        # check if bucket exists
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        print(f"allBuckets: {buckets}")
        self.assertIn(source_bucket_name, buckets, f"Bucket {source_bucket_name} not found")
        self.assertIn(destination_bucket_name, buckets, f"Bucket {destination_bucket_name} not found")
        # Upload a test file
        test_file_key = 'Flu_Vaccinations_v5_YGM41_20240732T12130100.csv'
        test_file_content = "example content"
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body=test_file_content)

        # Prepare the event
        event = {
            'Records': [
                {
                    's3': {
                        'bucket': {'name': source_bucket_name},
                        'object': {'key': test_file_key}
                    }
                }
            ]
        }

        # Call the lambda_handler function
        lambda_handler(event, None)
        # check no message was sent
        mock_send_to_supplier_queue.assert_not_called()
        # Check if the acknowledgment file is created in the S3 bucket
        ack_file_key = "ack/Flu_Vaccinations_v5_YGM41_20240732T12130100_response.csv"
        ack_files = s3_client.list_objects_v2(
            Bucket=destination_bucket_name
        )
        ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
        self.assertIn(ack_file_key, ack_file_keys)

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.sqs_client')
    @patch('processing_lambda.send_to_sqs')
    def test_e2e_successful_conversion(self, mock_send_to_sqs_message, mock_delete_message):
        # Mock S3 and SQS setup

        s3 = boto3.client('s3', region_name='eu-west-2')
        bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={
            'LocationConstraint': 'eu-west-2'
        })
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        s3.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={
            'LocationConstraint': 'eu-west-2'
        })

        # Define the mock response for the head_object method
        mock_head_object_response = {
            'LastModified': datetime(2024, 7, 30, 15, 22, 17)
        }

        vaccine_types = Constant.valid_vaccine_type
        for vaccine_type in vaccine_types:
            # Mock the fetch_file_from_s3 function
            with patch('processing_lambda.fetch_file_from_s3', return_value=Constant.file_content), \
                    patch('processing_lambda.s3_client.head_object', return_value=mock_head_object_response):
                # Mock SQS and send a test message
                sqs = boto3.client('sqs', region_name='eu-west-2')
                queue_url = sqs.create_queue(QueueName='EMIS_metadata_queue')['QueueUrl']
                message_body = {
                    'vaccine_type': vaccine_type,
                    'supplier': 'Pfizer',
                    'timestamp': '20210730T12000000'
                }
                sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))

                # Mock environment variables
                with patch.dict('os.environ', {
                    'ENVIRONMENT': 'internal-dev',
                    'INTERNAL_DEV_ACCOUNT_ID': '123456',
                    'ACK_BUCKET_NAME': ack_bucket_name
                }):
                    # Run the lambda_handler function
                    process_lambda_handler({}, {})

                    # Verify that the acknowledgment file has been created in the destination bucket
                    ack_key = f'processedFile/{vaccine_type}_Vaccinations_v5_Pfizer_20210730T12000000_response.csv'
                    ack_file = s3.get_object(Bucket=ack_bucket_name, Key=ack_key)['Body'].read().decode('utf-8')
                    self.assertIn('Success', ack_file)
                    mock_send_to_sqs_message.assert_called()
                    mock_delete_message.delete_message(QueueUrl=queue_url, ReceiptHandle=any)

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.sqs_client')
    @patch('processing_lambda.send_to_sqs')
    def test_e2e_processing_invalid_data(self, mock_send_to_sqs_message, mock_delete_message):
        # Set up the S3 environment
        s3 = boto3.client('s3', region_name='eu-west-2')
        bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={
            'LocationConstraint': 'eu-west-2'
        })
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        s3.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={
            'LocationConstraint': 'eu-west-2'
        })
        # Define the mock response for the head_object method
        mock_head_object_response = {
                'LastModified': datetime(2024, 7, 30, 15, 22, 17)
            }
        vaccine_types = Constant.valid_vaccine_type
        for vaccine_type in vaccine_types:
            # Mock the fetch_file_from_s3 function
            with patch('processing_lambda.fetch_file_from_s3', return_value=Constant.invalid_file_content), \
                    patch('processing_lambda.s3_client.head_object', return_value=mock_head_object_response):
                # Mock SQS and send a test message
                sqs = boto3.client('sqs', region_name='eu-west-2')
                queue_url = sqs.create_queue(QueueName='EMIS_metadata_queue')['QueueUrl']
                message_body = {
                    'vaccine_type': vaccine_type,
                    'supplier': 'Pfizer',
                    'timestamp': '20210730T12000000'
                }
                sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))

                # Mock environment variables
                with patch.dict('os.environ', {
                    'ENVIRONMENT': 'internal-dev',
                    'INTERNAL_DEV_ACCOUNT_ID': '123456',
                    'ACK_BUCKET_NAME': ack_bucket_name
                }):
                    # Run the lambda_handler function
                    process_lambda_handler({}, {})

                # Verify that the acknowledgment file has been created in S3
                ack_bucket = 'immunisation-batch-internal-dev-batch-data-destination'
                ack_key = f'processedFile/{vaccine_type}_Vaccinations_v5_Pfizer_20210730T12000000_response.csv'
                ack_file = s3.get_object(Bucket=ack_bucket, Key=ack_key)['Body'].read().decode('utf-8')
                self.assertIn('fatal-error', ack_file)
                self.assertIn('Unsupported file type received as an attachment', ack_file)
                mock_send_to_sqs_message.assert_not_called()
                mock_delete_message.delete_message(QueueUrl=queue_url, ReceiptHandle=any)


if __name__ == '__main__':
    unittest.main()
