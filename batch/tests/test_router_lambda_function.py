import unittest
from unittest.mock import patch, MagicMock
from router_lambda_function import (
    identify_supplier,
    identify_disease_type,
    identify_timestamp,
    initial_file_validation,
    send_to_supplier_queue,
    create_ack_file,
    extract_ods_code,
    validate_csv_column_count
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

    @patch('router_lambda_function.validate_csv_column_count')
    def test_valid_file(self, mock_validate_csv):
        mock_validate_csv.return_value = (True, [])
        file_key = 'Flu_Vaccinations_v5_YGM41_20240708T12130100.csv'
        bucket_name = 'test-bucket'

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertTrue(valid)
        self.assertFalse(errors)

    @patch('router_lambda_function.validate_csv_column_count')
    def test_invalid_extension(self, mock_validate_csv):
        file_key = 'Flu_Vaccinations_v5_YGM41_20240708T12130100.txt'
        bucket_name = 'test-bucket'

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch('router_lambda_function.validate_csv_column_count')
    def test_invalid_file_structure(self, mock_validate_csv):
        file_key = 'Flu_Vaccinations_v5_YGM41.csv'
        bucket_name = 'test-bucket'

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch('router_lambda_function.validate_csv_column_count')
    def test_invalid_disease_type(self, mock_validate_csv):
        file_key = 'Invalid_Vaccinations_v5_YGM41_20240708T12130100.csv'
        bucket_name = 'test-bucket'

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch('router_lambda_function.validate_csv_column_count')
    def test_invalid_version(self, mock_validate_csv):
        file_key = 'Flu_Vaccinations_v3_YGM41_20240708T12130100.csv'
        bucket_name = 'test-bucket'

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch('router_lambda_function.validate_csv_column_count')
    def test_invalid_ods_code(self, mock_validate_csv):
        file_key = 'Flu_Vaccinations_v5_INVALID_20240708T12130100.csv'
        bucket_name = 'test-bucket'

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch('router_lambda_function.validate_csv_column_count')
    def test_invalid_timestamp(self, mock_validate_csv):
        file_key = 'Flu_Vaccinations_v5_YGM41_20240708Ta99999999.csv'
        bucket_name = 'test-bucket'

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertTrue(errors)

    @patch('router_lambda_function.validate_csv_column_count')
    def test_invalid_column_count(self, mock_validate_csv):
        mock_validate_csv.return_value = (False, True)
        file_key = 'Flu_Vaccinations_v5_YGM41_20240708T12130100.csv'
        bucket_name = 'test-bucket'

        valid, errors = initial_file_validation(file_key, bucket_name)
        self.assertFalse(valid)
        self.assertEqual(errors, True)

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
        ack_bucket_name = "immunisation-fhir-api-internal-dev-batch-data-destination"
        validation_passed = True
        create_ack_file(self.file_key, ack_bucket_name, validation_passed)
        mock_s3_client.upload_fileobj.assert_called_once()
