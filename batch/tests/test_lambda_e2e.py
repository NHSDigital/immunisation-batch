
import unittest
from unittest.mock import patch, MagicMock
from router_lambda_function import (
    lambda_handler  # Import lambda_handler for end-to-end test
)


class TestRouterLambdaFunctionEndToEnd(unittest.TestCase):

    @patch.dict('os.environ', {'ENVIRONMENT': 'int'})  # Set environment variable for testing
    @patch('router_lambda_function.s3_client')
    @patch('router_lambda_function.sqs_client')
    def test_lambda_handler(self, mock_sqs_client, mock_s3_client):
        # Mock S3 event
        event = {
            "Records": [
                {
                    "eventVersion": "2.1",
                    "eventSource": "aws:s3",
                    "awsRegion": "us-west-2",
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
                            "key": "Flu_Vaccinations_v5_YYY55_20240708T12130100.csv",
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

        # Invoke Lambda function
        lambda_handler(event, None)

        # Assertions
        mock_s3_client.upload_fileobj.assert_called_once()
        mock_sqs_client.send_message.assert_called_once()
