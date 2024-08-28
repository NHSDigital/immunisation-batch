import boto3
import unittest
import json
from unittest.mock import patch, MagicMock
from moto import mock_s3, mock_sqs
from datetime import datetime
from src.constants import Constant
from io import StringIO, BytesIO
import csv


from processing_lambda import process_lambda_handler


class TestLambdaHandler(unittest.TestCase):

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.sqs_client')
    @patch('processing_lambda.send_to_sqs')
    @patch('csv.DictReader')
    def test_e2e_successful_conversion(self, mock_csv_dict_reader, mock_send_to_sqs, mock_sqs_client):
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
        mock_download_fileobj = Constant.mock_download_fileobj
        response = {
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

        vaccine_types = Constant.valid_vaccine_type  # Example valid vaccine types
        suppilers = Constant.valid_supplier
        ods_codes = Constant.valid_ods_codes  # Example valid ODS codes

        for vaccine_type in vaccine_types:
            for supplier in suppilers:
                for ods_code in ods_codes:
                    with patch('processing_lambda.fetch_file_from_s3', return_value=Constant.string_return), \
                         patch('processing_lambda.s3_client.head_object', return_value=mock_head_object_response), \
                         patch('processing_lambda.ImmunizationApi.get_imms_id', return_value=response), \
                         patch('processing_lambda.s3_client.download_fileobj', return_value=mock_download_fileobj):
                        mock_csv_reader_instance = MagicMock()
                        mock_csv_reader_instance = MagicMock()
                        mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
                        mock_csv_dict_reader.return_value = mock_csv_reader_instance
                        # Mock SQS and send a test message
                        sqs = boto3.client('sqs', region_name='eu-west-2')
                        queue_url = sqs.create_queue(QueueName='EMIS_metadata_queue')['QueueUrl']
                        message_body = {
                            'vaccine_type': vaccine_type,
                            'supplier': supplier,
                            'filename': f'{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv'
                        }
                        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))

                        # Mock environment variables
                        with patch.dict('os.environ', {
                            'ENVIRONMENT': 'internal-dev',
                            'LOCAL_ACCOUNT_ID': '123456',
                            'ACK_BUCKET_NAME': ack_bucket_name,
                            'SHORT_QUEUE_PREFIX': 'imms-batch-internal-dev'
                        }):
                            # Initialize the acknowledgment file with headers
                            ack_key = (
                                        f'processedFile/{vaccine_type}_Vaccinations_v5_'
                                        f'{ods_code}_20210730T12000000_response.csv'
                                    )
                            headers = Constant.headers
                            csv_buffer = StringIO()
                            csv_writer = csv.writer(csv_buffer, delimiter='|')
                            csv_writer.writerow(headers)
                            csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))

                            s3.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)

                            # Run the lambda_handler function
                            event = {
                                'Records': [{'body': json.dumps(message_body)}]
                            }
                            process_lambda_handler(event, {})

                            # Verify that the acknowledgment file has been updated in the destination bucket
                            ack_file = s3.get_object(Bucket=ack_bucket_name, Key=ack_key)['Body'].read().decode('utf-8')

                            print(f"Content of ack file: {ack_file}")  # Debugging print statement

                            self.assertIn('ok', ack_file)
                            mock_send_to_sqs.assert_called()

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.sqs_client')
    @patch('processing_lambda.send_to_sqs')
    @patch('csv.DictReader')
    def test_e2e_successful_conversion_sqs_failed(self, mock_csv_dict_reader, mock_send_to_sqs, mock_sqs_client):
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
        mock_download_fileobj = Constant.mock_download_fileobj
        response = {
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
        vaccine_types = Constant.valid_vaccine_type  # Example valid vaccine types
        suppilers = Constant.valid_supplier
        ods_codes = Constant.valid_ods_codes
        for vaccine_type in vaccine_types:
            for supplier in suppilers:
                for ods_code in ods_codes:
                    # Mock the fetch_file_from_s3 function
                    with patch('processing_lambda.fetch_file_from_s3', return_value=Constant.string_return), \
                         patch('processing_lambda.s3_client.head_object', return_value=mock_head_object_response), \
                         patch('processing_lambda.ImmunizationApi.get_imms_id', return_value=response), \
                         patch('processing_lambda.s3_client.download_fileobj', return_value=mock_download_fileobj), \
                         patch('processing_lambda.send_to_sqs', return_value=False):
                        # Mock SQS and send a test message
                        mock_csv_reader_instance = MagicMock()
                        mock_csv_reader_instance = MagicMock()
                        mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
                        mock_csv_dict_reader.return_value = mock_csv_reader_instance
                        sqs = boto3.client('sqs', region_name='eu-west-2')
                        queue_url = sqs.create_queue(QueueName='EMIS_metadata_queue')['QueueUrl']
                        message_body = {
                            'vaccine_type': vaccine_type,
                            'supplier': supplier,
                            'filename': f'{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv'
                        }
                        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))

                        # Mock environment variables
                        with patch.dict('os.environ', {
                            'ENVIRONMENT': 'internal-dev',
                            'LOCAL_ACCOUNT_ID': '123456',
                            'ACK_BUCKET_NAME': ack_bucket_name,
                            'SHORT_QUEUE_PREFIX': 'imms-batch-internal-dev'
                        }):
                            # Initialize the acknowledgment file with headers
                            ack_key = (
                                        f'processedFile/{vaccine_type}_Vaccinations_v5_'
                                        f'{ods_code}_20210730T12000000_response.csv'
                                    )
                            headers = Constant.headers
                            csv_buffer = StringIO()
                            csv_writer = csv.writer(csv_buffer, delimiter='|')
                            csv_writer.writerow(headers)
                            csv_buffer.seek(0)
                            csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))

                            s3.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)

                            # Run the lambda_handler function
                            event = {
                                'Records': [{'body': json.dumps(message_body)}]
                            }
                            # Run the lambda_handler function
                            process_lambda_handler(event, {})

                            # Verify that the acknowledgment file has been created in the destination bucket
                            ack_file = s3.get_object(Bucket=ack_bucket_name, Key=ack_key)['Body'].read().decode('utf-8')

                            print(f"Content of ack file: {ack_file}")  # Debugging print statement

                            self.assertIn('fatal-error', ack_file)
                            mock_send_to_sqs.assert_not_called()

    @mock_s3
    @mock_sqs
    @patch('processing_lambda.sqs_client')
    @patch('processing_lambda.send_to_sqs')
    @patch('csv.DictReader')
    def test_e2e_processing_invalid_data(self, mock_csv_dict_reader, mock_send_to_sqs, mock_sqs_client):
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
        mock_download_fileobj = Constant.mock_download_fileobj
        response = {
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
        vaccine_types = Constant.valid_vaccine_type  # Example valid vaccine types
        suppilers = Constant.valid_supplier
        ods_codes = Constant.valid_ods_codes
        for vaccine_type in vaccine_types:
            for supplier in suppilers:
                for ods_code in ods_codes:
                    # Mock the fetch_file_from_s3 function
                    with patch('processing_lambda.fetch_file_from_s3', return_value=Constant.invalid_file_content), \
                         patch('processing_lambda.convert_to_fhir_json', return_value={False, None}), \
                         patch('processing_lambda.s3_client.head_object', return_value=mock_head_object_response), \
                         patch('processing_lambda.ImmunizationApi.get_imms_id', return_value=response), \
                         patch('processing_lambda.s3_client.download_fileobj', return_value=mock_download_fileobj):
                        mock_csv_reader_instance = MagicMock()
                        mock_csv_reader_instance = MagicMock()
                        mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_request)
                        mock_csv_dict_reader.return_value = mock_csv_reader_instance
                        # Mock SQS and send a test message
                        sqs = boto3.client('sqs', region_name='eu-west-2')
                        queue_url = sqs.create_queue(QueueName='EMIS_metadata_queue')['QueueUrl']
                        message_body = {
                            'vaccine_type': vaccine_type,
                            'supplier': supplier,
                            'filename': f'{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv'
                        }
                        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))

                        # Mock environment variables
                        with patch.dict('os.environ', {
                            'ENVIRONMENT': 'internal-dev',
                            'LOCAL_ACCOUNT_ID': '123456',
                            'ACK_BUCKET_NAME': ack_bucket_name,
                            'SHORT_QUEUE_PREFIX': 'imms-batch-internal-dev'
                        }):
                            # Initialize the acknowledgment file with headers
                            ack_key = (
                                        f'processedFile/{vaccine_type}_Vaccinations_v5_'
                                        f'{ods_code}_20210730T12000000_response.csv'
                                    )
                            headers = Constant.headers
                            csv_buffer = StringIO()
                            csv_writer = csv.writer(csv_buffer, delimiter='|')
                            csv_writer.writerow(headers)
                            csv_buffer.seek(0)
                            csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))

                            s3.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)
                            event = {
                                'Records': [{'body': json.dumps(message_body)}]
                            }

                            # Run the lambda_handler function
                            process_lambda_handler(event, {})

                            # Verify that the acknowledgment file has been created in the destination bucket
                            ack_file = s3.get_object(Bucket=ack_bucket_name, Key=ack_key)['Body'].read().decode('utf-8')

                            print(f"Content of ack file: {ack_file}")  # Debugging print statement
                            self.assertIn('fatal-error', ack_file)
                            mock_send_to_sqs.assert_called()

    # @mock_s3
    # @mock_sqs
    # @patch('processing_lambda.sqs_client')
    # @patch('processing_lambda.send_to_sqs')
    # @patch('csv.DictReader')
    # def test_e2e_processing_imms_id_missing(self, mock_csv_dict_reader, mock_send_to_sqs_message,
    # mock_delete_message):
    #     # Set up the S3 environment
    #     s3 = boto3.client('s3', region_name='eu-west-2')
    #     bucket_name = 'immunisation-batch-internal-dev-batch-data-source'
    #     s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={
    #         'LocationConstraint': 'eu-west-2'
    #     })
    #     ack_bucket_name = 'immunisation-batch-internal-dev-batch-data-destination'
    #     s3.create_bucket(Bucket=ack_bucket_name, CreateBucketConfiguration={
    #         'LocationConstraint': 'eu-west-2'
    #     })
    #     # Define the mock response for the head_object method
    #     mock_head_object_response = {
    #             'LastModified': datetime(2024, 7, 30, 15, 22, 17)
    #         }
    #     mock_download_fileobj = Constant.mock_download_fileobj
    #     response = {"total": 0}, 404
    #     vaccine_types = Constant.valid_vaccine_type
    #     suppilers = Constant.valid_supplier
    #     ods_codes = Constant.valid_ods_codes
    #     for vaccine_type in vaccine_types:
    #         for supplier in suppilers:
    #             for ods_code in ods_codes:
    #                 #   Mock the fetch_file_from_s3 function
    #                 with patch('processing_lambda.fetch_file_from_s3', return_value=Constant.string_update_return), \
    #                      patch('processing_lambda.s3_client.head_object', return_value=mock_head_object_response), \
    #                      patch('processing_lambda.ImmunizationApi.create_imms', return_value=response), \
    #                      patch('processing_lambda.s3_client.download_fileobj', return_value=mock_download_fileobj):
    #                     mock_csv_reader_instance = MagicMock()
    #                     mock_csv_reader_instance = MagicMock()
    #                     mock_csv_reader_instance.__iter__.return_value = iter(Constant.mock_update_request)
    #                     mock_csv_dict_reader.return_value = mock_csv_reader_instance
    #                     # Mock SQS and send a test message
    #                     sqs = boto3.client('sqs', region_name='eu-west-2')
    #                     queue_url = sqs.create_queue(QueueName='EMIS_metadata_queue')['QueueUrl']
    #                     message_body = {
    #                         'vaccine_type': vaccine_type,
    #                         'supplier': supplier,
    #                         'filename': f'{vaccine_type}_Vaccinations_v5_{ods_code}_20210730T12000000.csv'
    #                     }
    #                     sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body))

    #                     # Mock environment variables
    #                     with patch.dict('os.environ', {
    #                         'ENVIRONMENT': 'internal-dev',
    #                         'LOCAL_ACCOUNT_ID': '123456',
    #                         'ACK_BUCKET_NAME': ack_bucket_name,
    #                         'SHORT_QUEUE_PREFIX': 'imms-batch-internal-dev'
    #                     }):

    #                         # Initialize the acknowledgment file with headers
    #                         ack_key = (
    #                                     f'processedFile/{vaccine_type}_Vaccinations_v5_'
    #                                     f'{ods_code}_20210730T12000000_response.csv'
    #                                 )
    #                         headers = Constant.headers
    #                         csv_buffer = StringIO()
    #                         csv_writer = csv.writer(csv_buffer, delimiter='|')
    #                         csv_writer.writerow(headers)
    #                         csv_buffer.seek(0)
    #                         csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))

    #                         s3.upload_fileobj(csv_bytes, ack_bucket_name, ack_key)
    #                         # Run the lambda_handler function
    #                         event = {
    #                             'Records': [{'body': json.dumps(message_body)}]
    #                         }
    #                         process_lambda_handler(event, {})

    #                     # Verify that the acknowledgment file has been created in S3
    #                     ack_bucket = 'immunisation-batch-internal-dev-batch-data-destination'
    #                     ack_key = (
    #                                     f'processedFile/{vaccine_type}_Vaccinations_v5_'
    #                                     f'{ods_code}_20210730T12000000_response.csv'
    #                                 )
    #                     ack_file = s3.get_object(Bucket=ack_bucket, Key=ack_key)['Body'].read().decode('utf-8')
    #                     self.assertIn('fatal-error', ack_file)
    #                     self.assertIn('Unsupported file type received as an attachment', ack_file)
    #                     mock_send_to_sqs_message.assert_not_called()


if __name__ == '__main__':
    unittest.main()
