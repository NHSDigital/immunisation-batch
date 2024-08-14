import unittest
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_s3, mock_sqs
from src.constants import Constant
import json
from processing_lambda import (
    process_lambda_handler, fetch_file_from_s3, process_csv_to_fhir, write_to_ack_file, get_environment
)


class TestProcessLambdaFunction(unittest.TestCase):
    @patch('processing_lambda.sqs_client')
    @patch('processing_lambda.process_csv_to_fhir')
    @patch('processing_lambda.boto3.client')
    def test_lambda_handler(self, mock_boto_client, mock_process_csv_to_fhir, mock_sqs_client):
        # Mock SQS client.
        mock_sqs_client_instance = MagicMock()
        mock_sqs_client.return_value = mock_sqs_client_instance

        # Mock S3 client
        mock_s3_client_instance = MagicMock()
        mock_boto_client.return_value = mock_s3_client_instance

        # Set up the queue URL and message body
        message_body = {
            'vaccine_type': 'COVID19',
            'supplier': 'Pfizer',
            'filename': 'testfile.csv'
        }

        # Mock SQS receive_message to return a predefined message
        mock_sqs_client_instance.receive_message.return_value = {
            'Messages': [{
                'MessageId': '1',
                'ReceiptHandle': 'dummy-receipt-handle',
                'Body': json.dumps(message_body)
            }]
        }

        # Patch environment variables
        with patch.dict('os.environ', {
            'PROD_ACCOUNT_ID': '123456789012',
            'LOCAL_ACCOUNT_ID': 'local-123',
            'ENVIRONMENT': 'internal-dev',
            'ACK_BUCKET_NAME': 'ack-bucket'
        }):
            # Invoke the lambda handler
            event = {
                'Records': [{
                    'body': json.dumps(message_body)
                }]
            }
            process_lambda_handler(event, {})

            # Assert process_csv_to_fhir was called with correct arguments
            mock_process_csv_to_fhir.assert_called_once_with(
                'ack-bucket',
                'testfile.csv',
                'Pfizer',
                'COVID19',
                'ack-bucket'
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
    def test_process_csv_to_fhir(self, mock_send_to_sqs):
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
        results = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": (
                        "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
                        "Immunization?immunization.identifier=https://supplierABC/identifiers/"
                        "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
                    )
                }
            ],
            "entry": [
                {
                    "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
                    "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
                    "resource": {
                        "resourceType": "Immunization",
                        "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
                        "meta": {
                            "versionId": 1
                        }
                    }
                }
            ],
            "total": 1
        }, 200
        with patch('processing_lambda.convert_to_fhir_json', return_value=({}, True)), \
             patch('processing_lambda.ImmunizationApi.get_imms_id', return_value=results):
            process_csv_to_fhir(bucket_name, file_key, sqs_queue_url, 'covid19', ack_bucket_name)

        ack_filename = 'processedFile/test-file_response.csv'
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response['Body'].read().decode('utf-8')
        self.assertIn('Success', content)
        mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.send_to_sqs')
    def test_process_csv_to_fhir_failed(self, mock_send_to_sqs):
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
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=Constant.file_content_id_missing)

        sqs_client = boto3.client('sqs', region_name='eu-west-2')
        sqs_queue_url = sqs_client.create_queue(QueueName='EMIS_processing_queue')['QueueUrl']
        results = {"total": 0}, 404
        with patch('processing_lambda.convert_to_fhir_json', return_value=({}, True)), \
             patch('processing_lambda.ImmunizationApi.get_imms_id', return_value=results):
            process_csv_to_fhir(bucket_name, file_key, sqs_queue_url, 'covid19', ack_bucket_name)

        ack_filename = 'processedFile/test-file_response.csv'
        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response['Body'].read().decode('utf-8')
        self.assertIn('fatal-error', content)
        mock_send_to_sqs.assert_not_called()

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.send_to_sqs')
    def test_process_csv_to_fhir_successful(self, mock_send_to_sqs):
        s3_client = boto3.client('s3', region_name='us-west-2')
        bucket_name = 'test-bucket'
        file_key = 'test-file.csv'
        ack_bucket_name = 'ack-bucket'
        csv_content = Constant.file_content
        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.put_object(Bucket=bucket_name, Key=file_key, Body=csv_content)

        sqs_client = boto3.client('sqs', region_name='eu-west-2')
        sqs_queue_url = sqs_client.create_queue(QueueName='EMIS_processing_queue')['QueueUrl']
        results = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": (
                        "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
                        "Immunization?immunization.identifier=https://supplierABC/identifiers/"
                        "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
                    )
                }
            ],
            "entry": [
                {
                    "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
                    "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
                    "resource": {
                        "resourceType": "Immunization",
                        "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
                        "meta": {
                            "versionId": 1
                        }
                    }
                }
            ],
            "total": 1
        }, 200
        vaccine_types = Constant.valid_vaccine_type
        for vaccine_type in vaccine_types:
            with patch('processing_lambda.ImmunizationApi.get_imms_id', return_value=results):
                process_csv_to_fhir(bucket_name, file_key, sqs_queue_url, vaccine_type, ack_bucket_name)

            ack_filename = 'processedFile/test-file_response.csv'
            response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
            content = response['Body'].read().decode('utf-8')
            self.assertIn('Success', content)
            mock_send_to_sqs.assert_called()

    @mock_s3
    def test_write_to_ack_file_append(self):
        s3_client = boto3.client('s3', region_name='us-west-2')
        ack_bucket_name = 'ack-bucket'
        ack_filename = 'test-ack-file.csv'
        existing_content = """MESSAGE_HEADER_ID|HEADER_RESPONSE_CODE|ISSUE_SEVERITY|ISSUE_CODE|RESPONSE_TYPE|
        RESPONSE_CODE|RESPONSE_DISPLAY|RECEIVED_TIME|MAILBOX_FROM|LOCAL_ID
existing_row"""
        new_row = ['TBC', 'ok', 'information', 'informational', 'business', '20013', 'Success',
                   '20210730T12000000', 'TBC', 'DPS']

        s3_client.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={
                                    'LocationConstraint': 'eu-west-2'
                                })
        s3_client.put_object(Bucket=ack_bucket_name, Key=ack_filename, Body=existing_content)

        with patch('processing_lambda.s3_client', s3_client):
            write_to_ack_file(ack_bucket_name, ack_filename, new_row)

        response = s3_client.get_object(Bucket=ack_bucket_name, Key=ack_filename)
        content = response['Body'].read().decode('utf-8')
        self.assertIn('existing_row', content)
        self.assertIn('|'.join(new_row), content)

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
