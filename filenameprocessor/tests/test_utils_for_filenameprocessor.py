"""Tests for utils_for_filenameprocessor functions"""

import unittest
import boto3
from unittest.mock import patch
from moto import mock_s3
from utils_for_filenameprocessor import (
    get_environment,
    get_csv_content_dict_reader,
    identify_supplier,
    extract_file_key_elements,
)
from constants import Constants


class TestUtilsForFilenameprocessor(unittest.TestCase):
    """Tests for utils_for_filenameprocessor functions"""

    def setUp(self):
        self.test_file_key = "test_file_key"
        self.test_bucket_name = "test_bucket"

    def setup_s3_bucket_and_file(self, test_bucket_name, test_file_key, test_file_content=Constants.valid_file_content):
        """
        Sets up the S3 client and uploads the test file, containing the test file content, to a bucket named
        'test_bucket'. Returns the S3 client
        """
        s3_client = boto3.client("s3", region_name="eu-west-2")
        s3_client.create_bucket(Bucket=test_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
        s3_client.put_object(Bucket=test_bucket_name, Key=test_file_key, Body=test_file_content)
        return s3_client

    def test_get_environment(self):
        "Tests that get_environment returns the correct environment"
        test_values = {
            "internal-dev": "internal-dev",
            "int": "int",
            "ref": "ref",
            "sandbox": "sandbox",
            "prod": "prod",
            "pr-22": "internal-dev",
        }

        for test_value, expected_result in test_values.items():
            with self.subTest():
                with patch("os.getenv", return_value=test_value):
                    self.assertEqual(get_environment(), expected_result)

    @mock_s3
    def test_get_csv_content_dict_reader(self):
        """Test that get_csv_content_dict_reader can download and correctly read the data file"""
        test_file_content = "HEADER1|HEADER2\nvalue1|value2"
        s3_client = self.setup_s3_bucket_and_file(self.test_bucket_name, self.test_file_key, test_file_content)

        csv_content_dict_reader = get_csv_content_dict_reader(self.test_bucket_name, self.test_file_key, s3_client)

        for row in csv_content_dict_reader:
            self.assertEqual(row.get("HEADER1"), "value1")
            self.assertEqual(row.get("HEADER2"), "value2")

    def test_identify_supplier(self):
        """Test that identify_supplier correctly identifies supplier using ods_to_supplier_mappings"""
        test_values = {
            "YGM41": "EMIS",
            "8J1100001": "PINNACLE",
            "8HK48": "SONAR",
            "YGA": "TPP",
            "0DE": "AGEM-NIVS",
            "0DF": "NIMS",
            "8HA94": "EVA",
            "X26": "RAVS",
            "YGMYH": "MEDICAL_DIRECTOR",
            "W00": "WELSH_DA_1",
            "W000": "WELSH_DA_2",
            "ZT001": "NORTHERN_IRELAND_DA",
            "YA7": "SCOTLAND_DA",
            "N2N9I": "COVID19_VACCINE_RESOLUTION_SERVICEDESK",
            "YGJ": "EMIS",
            "DPSREDUCED": "DPSREDUCED",
            "DPSFULL": "DPSFULL",
            "NOT_A_VALID_ODS_CODE": "",  # Should default to empty string if ods code isn't in the mappings
        }

        for test_value, expected_result in test_values.items():
            with self.subTest():
                self.assertEqual(identify_supplier(test_value), expected_result)

    def test_extract_file_key_elements(self):
        """
        Test that for any string which ends in .csv and has 4 underscores and a single '.',
        extract_file_key_elements returns the correct file_key_elements.
        """
        # TEST CASE: Valid covid19 dpsfull file, all lowercase
        file_key_1 = "covid19_vaccinations_v5_dpsfull_2020010100.csv"
        expected_file_key_elements_1 = {
            "vaccine_type": "COVID19",
            "vaccination": "VACCINATIONS",
            "version": "V5",
            "ods_code": "DPSFULL",
            "timestamp": "2020010100",
            "extension": "CSV",
            "supplier": "DPSFULL",
        }

        # TEST CASE: Valid flu emis file, all uppercase
        file_key_2 = "FLU_VACCINATIONS_V5_YGM41_2020010100.csv"
        expected_file_key_elements_2 = {
            "vaccine_type": "FLU",
            "vaccination": "VACCINATIONS",
            "version": "V5",
            "ods_code": "YGM41",
            "timestamp": "2020010100",
            "extension": "CSV",
            "supplier": "EMIS",
        }

        # TEST CASE: Covid19 file with invalid version and odscode, mix of upper and lower case
        file_key_3 = "CoVid19_VACCINATIoNS_invalidVersion_inValidOds_2020010100.csv"
        expected_file_key_elements_3 = {
            "vaccine_type": "COVID19",
            "vaccination": "VACCINATIONS",
            "version": "INVALIDVERSION",
            "ods_code": "INVALIDODS",
            "timestamp": "2020010100",
            "extension": "CSV",
            "supplier": "",
        }

        # TEST CASE: EMIS file with invalid vaccine type, vaccinations section and timestamp
        file_key_4 = "invalidVaccine_invalidText_v5_ygm41_notATimestamp.csv"
        expected_file_key_elements_4 = {
            "vaccine_type": "INVALIDVACCINE",
            "vaccination": "INVALIDTEXT",
            "version": "V5",
            "ods_code": "YGM41",
            "timestamp": "NOTATIMESTAMP",
            "extension": "CSV",
            "supplier": "EMIS",
        }

        # TEST CASE: Vaccine type, version and timestamp missing
        file_key_5 = "_vaccinations__ygm41_.csv"
        expected_file_key_elements_5 = {
            "vaccine_type": "",
            "vaccination": "VACCINATIONS",
            "version": "",
            "ods_code": "YGM41",
            "timestamp": "",
            "extension": "CSV",
            "supplier": "EMIS",
        }

        # TEST CASE: Flu file missing the vaccinations section and ODS code
        file_key_6 = "Flu__v5__2020010100.csv"
        expected_file_key_elements_6 = {
            "vaccine_type": "FLU",
            "vaccination": "",
            "version": "V5",
            "ods_code": "",
            "timestamp": "2020010100",
            "extension": "CSV",
            "supplier": "",
        }

        test_values = {
            file_key_1: expected_file_key_elements_1,
            file_key_2: expected_file_key_elements_2,
            file_key_3: expected_file_key_elements_3,
            file_key_4: expected_file_key_elements_4,
            file_key_5: expected_file_key_elements_5,
            file_key_6: expected_file_key_elements_6,
        }

        for test_value, expected_result in test_values.items():
            with self.subTest():
                self.assertEqual(extract_file_key_elements(test_value), expected_result)
