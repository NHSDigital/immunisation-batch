import unittest
from unittest.mock import patch
from router_lambda_function import (
    identify_supplier,
    identify_disease_type,
    identify_timestamp,
    initial_file_validation,
    send_to_supplier_queue,
    create_ack_file,
    extract_ods_code,
)


class TestRouterLambdaFunctions(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        cls.ods_code = "YGM41"

    def test_identify_supplier(self):
        '''tests supplier is correctly matched'''
        supplier = identify_supplier(self.ods_code)
        print({supplier})
        self.assertEqual(supplier, "EMIS")

    def test_extract_ods_code(self):
        '''tests supplier ODS code is extracted'''
        ods_code = extract_ods_code(self.file_key)
        print({ods_code})
        self.assertEqual(ods_code, "YGM41")

    def test_identify_disease_type(self):
        '''tests disease type is extracted'''
        disease_type = identify_disease_type(self.file_key)
        print({disease_type})
        self.assertEqual(disease_type, "Flu")

    def test_identify_timestamp(self):
        '''tests timestamp is extracted'''
        timestamp = identify_timestamp(self.file_key)
        print({timestamp})
        self.assertEqual(timestamp, '20240708T12130100')

    def test_initial_file_validation_valid(self):
        '''test whether validation is passed'''
        validation_passed, validation_errors = initial_file_validation(self.file_key, "test_bucket")
        self.assertTrue(validation_passed)
        self.assertEqual(validation_errors, [])

    @patch('router_lambda_function.sqs_client')
    def test_send_to_supplier_queue(self, mock_sqs_client):
        '''tests if supplier queue is called'''
        mock_send_message = mock_sqs_client.send_message
        supplier = "YGM41"
        message_body = {
            'disease_type': 'Flu',
            'supplier': supplier,
            'timestamp': '20240708T12130100'
        }
        send_to_supplier_queue(supplier, message_body)
        mock_send_message.assert_called_once()

    @patch('router_lambda_function.s3_client')
    def test_create_ack_file(self, mock_s3_client):
        '''tests whether ack file is created'''
        bucket_name = "test_bucket"
        ack_bucket_name = "immunisation-fhir-api-internal-dev-batch-data-destination"
        validation_passed = True
        validation_errors = []
        create_ack_file(bucket_name, self.file_key, ack_bucket_name, validation_passed, validation_errors)
        mock_s3_client.upload_fileobj.assert_called_once()
