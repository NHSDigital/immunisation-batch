import unittest
from unittest.mock import patch
import boto3
import json
from moto import mock_s3, mock_sqs
from forwarding_lambda import forward_lambda_handler
from src.constants import Constant


class TestForwardingLambdaE2E(unittest.TestCase):

    @mock_s3
    @mock_sqs
    @patch('forwarding_lambda.immunization_api_instance')
    def test_forward_lambda_e2e_create_success(self, mock_api):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})
        s3_client.create_bucket(Bucket=ack_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})

        # Put a test file in the source S3 bucket
        test_file_key = 'test_file.csv'
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body='test_data')

        # Mock the API response
        mock_api.create_immunization.return_value = ('', 201)

        # Create a mock SQS message
        sqs_message = {
            "Records": [
                {
                    "body": json.dumps({
                        "fhir_json": "{}",
                        "action_flag": "new",
                        "file_name": test_file_key
                    })
                }
            ]
        }

        # Invoke the Lambda handler function
        forward_lambda_handler(sqs_message, None)

        # Check that the acknowledgment file was created in the destination S3 bucket
        ack_filename = f'forwardedFile/{test_file_key.split(".")[0]}_response.csv'
        ack_file_obj = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        ack_file_content = ack_file_obj['Body'].read().decode('utf-8')

        # Assert the acknowledgment file has the correct header and one data row

        self.assertIn('ok', ack_file_content)
        # Check that the mock API was called once
        mock_api.create_immunization.assert_called_once()

    @mock_s3
    @mock_sqs
    @patch('forwarding_lambda.immunization_api_instance')
    def test_forward_lambda_e2e_create_failed(self, mock_api):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})
        s3_client.create_bucket(Bucket=ack_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})

        # Put a test file in the source S3 bucket
        test_file_key = 'test_file.csv'
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body='test_data')

        # Mock the API response
        mock_api.create_immunization.return_value = ('', 400)

        # Create a mock SQS message
        sqs_message = {
            "Records": [
                {
                    "body": json.dumps({
                        "fhir_json": "{}",
                        "action_flag": "new",
                        "file_name": test_file_key
                    })
                }
            ]
        }

        # Invoke the Lambda handler function
        forward_lambda_handler(sqs_message, None)

        # Check that the acknowledgment file was created in the destination S3 bucket
        ack_filename = f'forwardedFile/{test_file_key.split(".")[0]}_response.csv'
        ack_file_obj = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        ack_file_content = ack_file_obj['Body'].read().decode('utf-8')

        # Assert the acknowledgment file has the correct header and one data row

        self.assertIn('fatal-error', ack_file_content)
        # Check that the mock API was called once
        mock_api.create_immunization.assert_called_once()

    @mock_s3
    @mock_sqs
    @patch('forwarding_lambda.immunization_api_instance')
    def test_forward_lambda_e2e_update_success(self, mock_api):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})
        s3_client.create_bucket(Bucket=ack_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})

        # Put a test file in the source S3 bucket
        test_file_key = 'test_file.csv'
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body='test_data')

        # Mock the API response
        mock_api.update_immunization.return_value = ('', 200)
        message = {
                        "fhir_json": Constant.test_fhir_json,
                        "action_flag": "update",
                        "file_name": test_file_key,
                        "imms_id": "test",
                        "version": 1
                    }

        # Create a mock SQS message
        sqs_message = {
            "Records": [
                {
                    "body": json.dumps(message)
                }
            ]
        }

        # Invoke the Lambda handler function
        forward_lambda_handler(sqs_message, None)

        # Check that the acknowledgment file was created in the destination S3 bucket
        ack_filename = f'forwardedFile/{test_file_key.split(".")[0]}_response.csv'
        ack_file_obj = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        ack_file_content = ack_file_obj['Body'].read().decode('utf-8')

        # Assert the acknowledgment file has the correct header and one data row

        self.assertIn('ok', ack_file_content)
        # Check that the mock API was called once
        mock_api.update_immunization.assert_called_once()

    @mock_s3
    @mock_sqs
    @patch('forwarding_lambda.immunization_api_instance')
    def test_forward_lambda_e2e_update_failed(self, mock_api):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})
        s3_client.create_bucket(Bucket=ack_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})

        # Put a test file in the source S3 bucket
        test_file_key = 'test_file.csv'
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body='test_data')

        # Mock the API response
        mock_api.update_immunization.return_value = ('', 400)

        message = {
                        "fhir_json": Constant.test_fhir_json,
                        "action_flag": "update",
                        "file_name": test_file_key,
                        "imms_id": "test",
                        "version": 1
                    }

        # Create a mock SQS message
        sqs_message = {
            "Records": [
                {
                    "body": json.dumps(message)
                }
            ]
        }

        # Invoke the Lambda handler function
        forward_lambda_handler(sqs_message, None)

        # Check that the acknowledgment file was created in the destination S3 bucket
        ack_filename = f'forwardedFile/{test_file_key.split(".")[0]}_response.csv'
        ack_file_obj = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        ack_file_content = ack_file_obj['Body'].read().decode('utf-8')

        # Assert the acknowledgment file has the correct header and one data row

        self.assertIn('fatal-error', ack_file_content)
        # Check that the mock API was called once
        mock_api.update_immunization.assert_called_once()

    @mock_s3
    @mock_sqs
    @patch('forwarding_lambda.immunization_api_instance')
    def test_forward_lambda_e2e_delete_success(self, mock_api):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})
        s3_client.create_bucket(Bucket=ack_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})

        # Put a test file in the source S3 bucket
        test_file_key = 'test_file.csv'
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body='test_data')

        # Mock the API response
        mock_api.delete_immunization.return_value = ('', 204)

        # Create a mock SQS message
        sqs_message = {
            "Records": [
                {
                    "body": json.dumps({
                        "fhir_json": "{}",
                        "action_flag": "delete",
                        "file_name": test_file_key,
                        "imms_id": "test",
                        "version": 1
                    })
                }
            ]
        }

        # Invoke the Lambda handler function
        forward_lambda_handler(sqs_message, None)

        # Check that the acknowledgment file was created in the destination S3 bucket
        ack_filename = f'forwardedFile/{test_file_key.split(".")[0]}_response.csv'
        ack_file_obj = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        ack_file_content = ack_file_obj['Body'].read().decode('utf-8')

        # Assert the acknowledgment file has the correct header and one data row

        self.assertIn('ok', ack_file_content)
        # Check that the mock API was called once
        mock_api.delete_immunization.assert_called_once()

    @mock_s3
    @mock_sqs
    @patch('forwarding_lambda.immunization_api_instance')
    def test_forward_lambda_e2e_delete_failed(self, mock_api):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='eu-west-2')
        source_bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        s3_client.create_bucket(Bucket=source_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})
        s3_client.create_bucket(Bucket=ack_bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': 'eu-west-2'})

        # Put a test file in the source S3 bucket
        test_file_key = 'test_file.csv'
        s3_client.put_object(Bucket=source_bucket_name, Key=test_file_key, Body='test_data')

        # Mock the API response
        mock_api.delete_immunization.return_value = ('', 404)

        # Create a mock SQS message
        sqs_message = {
            "Records": [
                {
                    "body": json.dumps({
                        "fhir_json": "{}",
                        "action_flag": "delete",
                        "file_name": test_file_key,
                        "imms_id": "test",
                        "version": 1
                    })
                }
            ]
        }

        # Invoke the Lambda handler function
        forward_lambda_handler(sqs_message, None)

        # Check that the acknowledgment file was created in the destination S3 bucket
        ack_filename = f'forwardedFile/{test_file_key.split(".")[0]}_response.csv'
        ack_file_obj = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        ack_file_content = ack_file_obj['Body'].read().decode('utf-8')

        # Assert the acknowledgment file has the correct header and one data row

        self.assertIn('fatal-error', ack_file_content)
        # Check that the mock API was called once
        mock_api.delete_immunization.assert_called_once()


if __name__ == '__main__':
    unittest.main()
