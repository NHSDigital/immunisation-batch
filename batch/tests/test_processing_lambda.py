import unittest
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_s3, mock_sqs
from src.constants import Constant
import json
from processing_lambda import (
    process_lambda_handler, fetch_file_from_s3, process_csv_to_fhir, create_ack_file, get_environment
)
from convert_fhir_json import convert_to_fhir_json


class TestProcessLambdaFunction(unittest.TestCase):
    @patch('processing_lambda.sqs_client')  # Replace with the correct import path
    @patch('processing_lambda.process_csv_to_fhir')  # Replace with the correct import path
    @patch('processing_lambda.boto3.client')  # Mock the boto3 client itself
    def test_lambda_handler(self, mock_boto_client, mock_process_csv_to_fhir, mock_delete_message):
        # Setup: Create the queue and mock tha receive_message response
        sqs = boto3.client('sqs', region_name='eu-west-2')
        queue_url = sqs.create_queue(QueueName='EMIS_metadata_queue')['QueueUrl']
        message_body = {
            'vaccine_type': 'COVID19',
            'supplier': 'Pfizer',
            'timestamp': '20210730T12000000'
        }
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))
        # Mock receive_message to return our test message
        mock_sqs_client = MagicMock()
        mock_sqs_client.receive_message.return_value = {
            'Messages': [{
                'MessageId': '1',
                'ReceiptHandle': 'dummy-receipt-handle',
                'Body': json.dumps(message_body)
            }]
        }
        mock_boto_client.return_value = mock_sqs_client

        # Mock environment variables
        with patch.dict('os.environ', {
            'INTERNAL-DEV_ACCOUNT_ID': '123456789012',
            'ENVIRONMENT': 'internal-dev',
            'ACK_BUCKET_NAME': 'ack-bucket'
        }):
            # Call the lambda handler
            process_lambda_handler({}, {})

            # Debug: Print call arguments for delete_message and process_csv_to_fhir
            print(f"delete_message call args: {mock_delete_message.call_args_list}")
            print(f"process_csv_to_fhir call args: {mock_process_csv_to_fhir.call_args_list}")

            # Check that process_csv_to_fhir was called once
            mock_process_csv_to_fhir.assert_called_once()

            # Check that delete_message was called with the correct parameters
            mock_delete_message.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=any
            )

    @mock_s3
    def test_fetch_file_from_s3(self):
        s3_client = boto3.client('s3', region_name='us-west-2')
        bucket_name = 'test-bucket'
        file_key = 'test-file.csv'

        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body='test content')

        with patch('processing_lambda.s3_client', s3_client):
            content = fetch_file_from_s3(bucket_name, file_key)
            self.assertEqual(content, 'test content')

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.send_to_sqs')
    def test_process_csv_to_fhir(self, mock_send_to_sqs_message):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-west-2')
        bucket_name = 'test-bucket'
        file_key = 'test-file.csv'
        ack_bucket_name = 'ack-bucket'
        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constant.file_content)
        sqs_client = boto3.client('sqs', region_name='eu-west-2')
        sqs_queue_url = sqs_client.create_queue(QueueName='EMIS_processing_queue')['QueueUrl']

        # Patch the convert_to_fhir_json function
        vaccine_types = ['covid19', 'flu', 'mmr']
        for vaccine_type in vaccine_types:
            with patch('processing_lambda.convert_to_fhir_json', return_value=({}, True)), \
                 patch('processing_lambda.ImmunizationApi.get_immunization_id', return_value={"statusCode": 200, "body": {"id":"1234","Version":1}}):

                process_csv_to_fhir(bucket_name, file_key, sqs_queue_url, vaccine_type, ack_bucket_name)

            # Check if the ack file was created
            ack_filename = 'processedFile/test-file_response.csv'
            response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
            content = response['Body'].read().decode('utf-8')
            self.assertIn('Success', content)
            mock_send_to_sqs_message.assert_called()

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.send_to_sqs')
    def test_process_csv_to_fhir_failed(self, mock_send_to_sqs_message):
        # Setup mock S3
        s3_client = boto3.client('s3', region_name='us-west-2')
        bucket_name = 'test-bucket'
        file_key = 'test-file.csv'
        ack_bucket_name = 'ack-bucket'
        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constant.file_content_imms_id_missing)
        sqs_client = boto3.client('sqs', region_name='eu-west-2')
        sqs_queue_url = sqs_client.create_queue(QueueName='EMIS_processing_queue')['QueueUrl']

        # Patch the convert_to_fhir_json function
        vaccine_types = ['covid19', 'flu', 'mmr']
        for vaccine_type in vaccine_types:
            with patch('processing_lambda.convert_to_fhir_json', return_value=({}, True)), \
                 patch('processing_lambda.ImmunizationApi.get_immunization_id', return_value={"statusCode": 404, "body": {"diagnostics": "The requested resource was not found."}}):

                process_csv_to_fhir(bucket_name, file_key, sqs_queue_url, vaccine_type, ack_bucket_name)

            # Check if the ack file was created
            ack_filename = 'processedFile/test-file_response.csv'
            response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
            content = response['Body'].read().decode('utf-8')
            self.assertIn('fatal-error', content)
            mock_send_to_sqs_message.assert_not_called()

    def test_convert_to_fhir_json_valid(self):
        vaccine_types = ['covid19', 'flu', 'mmr']
        for vaccine_type in vaccine_types:
            result, valid = convert_to_fhir_json(Constant.row, vaccine_type)
            self.assertTrue(valid)
            self.assertEqual(result['resourceType'], 'Immunization')

    @mock_s3
    def test_create_ack_file(self):
        # Mock S3 client
        s3_client = boto3.client('s3', region_name='us-west-2')
        ack_bucket_name = 'ack-bucket'
        file_key = 'test-file.csv'
        results = [{'valid': True, 'message': 'Success'}]
        created_at_formatted = '2024-07-08T12:13:01Z'

        # Create mock bucket
        s3_client.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={'LocationConstraint': 'us-west-2'})

        # Patch the s3_client in the module where create_ack_file is defined
        with patch('processing_lambda.s3_client', s3_client):  # Replace 'your_module_name' with the actual module name
            create_ack_file(file_key, ack_bucket_name, results, created_at_formatted)

            # List objects in the mock S3 bucket
            ack_files = s3_client.list_objects_v2(Bucket=ack_bucket_name)
            ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]

            # Check if the expected acknowledgment file exists in the bucket
            expected_file_key = f"processedFile/{file_key.split('.')[0]}_response.csv"
            self.assertIn(expected_file_key, ack_file_keys)

            # Additional assertions to verify the contents of the file could be added here if needed

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.send_to_sqs')
    def test_process_csv_to_fhir_valid_invalid_content(self, mock_send_to_sqs_message):
        s3_client = boto3.client('s3', region_name='us-west-2')
        bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
        ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
        file_key = 'test-file.csv'

        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=ack_bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body="ID,Name\n1,Test")
        sqs_client = boto3.client('sqs', region_name='eu-west-2')
        sqs_queue_url = sqs_client.create_queue(QueueName='EMIS_processing_queue')['QueueUrl']
        vaccine_types = ['covid19', 'flu', 'mmr']
        for vaccine_type in vaccine_types:
            with patch('processing_lambda.s3_client', s3_client):
                process_csv_to_fhir(bucket_name, file_key, sqs_queue_url, vaccine_type, ack_bucket_name)
                # Check if acknowledgment file is created
                ack_files = s3_client.list_objects_v2(Bucket=ack_bucket_name)
                ack_file_keys = [obj['Key'] for obj in ack_files.get('Contents', [])]
                self.assertIn(f"processedFile/{file_key.split('.')[0]}_response.csv", ack_file_keys)
                mock_send_to_sqs_message.assert_not_called()

    def test_get_environment(self):
        with patch('processing_lambda.os.getenv', return_value="internal-dev"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

        with patch('processing_lambda.os.getenv', return_value="prod"):
            env = get_environment()
            self.assertEqual(env, "prod")

        with patch('processing_lambda.os.getenv', return_value="unknown-env"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")


if __name__ == '__main__':
    unittest.main()
