"""Tests for initial_file_validation functions"""

import unittest
from unittest.mock import patch
from io import StringIO
import csv
import json
import boto3
from moto import mock_s3
from src.initial_file_validation import (
    is_valid_datetime,
    validate_content_headers,
    get_supplier_permissions,
    validate_vaccine_type_permissions,
    validate_action_flag_permissions,
    initial_file_validation,
)
from src.constants import Constants
from tests.utils_for_filenameprocessor_tests import setup_s3_bucket_and_file


def convert_string_to_dict_reader(data_string: str):
    """Convert a string to a csv dict reader"""
    return csv.DictReader(StringIO(data_string), delimiter="|")


class TestInitialFileValidation(unittest.TestCase):
    """Tests for utils_for_filenameprocessor functions"""

    def setUp(self):
        self.test_file_key = "Flu_Vaccinations_v5_DPSFULL_20200101T12345600.csv"
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

    def test_is_valid_datetime(self):
        "Tests that is_valid_datetime returns True for valid datetimes, and false otherwise"
        test_cases = {
            "20200101T12345600": True,  # Valid datetime string with timezone
            "20200101T123456": True,  # Valid datetime string without timezone
            "20200101T123456extracharacters": True,  # Valid datetime string with additional characters
            "20201301T12345600": False,  # Invalid month
            "20200100T12345600": False,  # Invalid day
            "20200230T12345600": False,  # Invalid combination of month and day
            "20200101T24345600": False,  # Invalid hours
            "20200101T12605600": False,  # Invalid minutes
            "20200101T12346000": False,  # Invalid seconds
            "2020010112345600": False,  # Invalid missing the 'T'
            "20200101T12345": False,  # Invalid string too short
        }

        for test_value, expected_result in test_cases.items():
            with self.subTest():
                self.assertEqual(is_valid_datetime(test_value), expected_result)

    def test_validate_content_headers(self):
        "Tests that validate_content_headers returns True for an exact header match and False otherwise"
        test_cases = {
            Constants.valid_file_content: True,  # Valid file content
            Constants.valid_file_content.replace("SITE_CODE", "SITE_COVE"): False,  # Misspelled header
            Constants.valid_file_content.replace("SITE_CODE|", ""): False,  # Missing header
            Constants.valid_file_content.replace("PERSON_DOB|", "PERSON_DOB|EXTRA_HEADER|"): False,  # Extra header
        }

        for test_value, expected_result in test_cases.items():
            with self.subTest():
                # validate_content_headers takes a csv dict reader as it's input
                test_data = convert_string_to_dict_reader(test_value)
                self.assertEqual(validate_content_headers(test_data), expected_result)

    @mock_s3
    def test_get_supplier_permissions(self):
        """Test that get_supplier_permissions returns the correct permsisions for the given supplier"""
        config_bucket_name = "test_config_bucket"
        permissions_json = {
            "all_permissions": {
                "TEST_SUPPLIER_1": ["COVID19_FULL", "FLU_FULL"],
                "TEST_SUPPLIER_2": ["FLU_CREATE", "FLU_DELETE"],
                "TEST_SUPPLIER_3": ["COVID19_CREATE", "COVID19_DELETE", "FLU_FULL"],
            },
        }
        setup_s3_bucket_and_file(
            test_bucket_name=config_bucket_name,
            test_file_key="permissions_config.json",
            test_file_content=json.dumps(permissions_json),
        )

        # Test case tuples are stuctured as (supplier, expected_result)
        test_cases = [
            ("TEST_SUPPLIER_1", ["COVID19_FULL", "FLU_FULL"]),
            ("TEST_SUPPLIER_2", ["FLU_CREATE", "FLU_DELETE"]),
            ("TEST_SUPPLIER_3", ["COVID19_CREATE", "COVID19_DELETE", "FLU_FULL"]),
        ]

        for supplier, expected_result in test_cases:
            with self.subTest():
                with (patch("src.initial_file_validation.os.getenv", return_value=config_bucket_name),):
                    self.assertEqual(get_supplier_permissions(supplier), expected_result)

    def test_validate_vaccine_type_permissions(self):
        """
        Tests that validate_vaccine_type_permissions returns True if supplier has permissions
        for the requested vaccine type and False otherwise
        """
        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions, expected_result)
        test_cases = [
            ("FLU", ["COVID19_CREATE", "FLU_FULL"], True),  # Full permissions for flu
            ("FLU", ["FLU_CREATE"], True),  # Create permissions for flu
            ("FLU", ["FLU_UPDATE"], True),  # Update permissions for flu
            ("FLU", ["FLU_DELETE"], True),  # Delete permissions for flu
            ("FLU", ["COVID19_FULL"], False),  # No permissions for flu
            ("COVID19", ["COVID19_FULL", "FLU_FULL"], True),  # Full permissions for COVID19
            ("COVID19", ["COVID19_CREATE", "FLU_FULL"], True),  # Create permissions for COVID19
            ("COVID19", ["FLU_CREATE"], False),  # No permissions for COVID19
        ]

        for vaccine_type, vaccine_permissions, expected_result in test_cases:
            with self.subTest():
                with patch("src.initial_file_validation.get_supplier_permissions", return_value=vaccine_permissions):
                    self.assertEqual(validate_vaccine_type_permissions("TEST_SUPPLIER", vaccine_type), expected_result)

    def test_validate_action_flag_permissions(self):
        """
        Tests that validate_action_flag_permissions returns True if supplier has permissions to perform at least one
        of the requested CRUD operations for the given vaccine type, and False otherwise
        """
        # Note that Constants.valid_file_content contains one "new" and one "update" ACTION_FLAG
        valid_file_content = Constants.valid_file_content
        valid_content_new_and_update_lowercase = valid_file_content
        valid_content_new_and_update_uppercase = valid_file_content.replace("new", "NEW").replace("update", "UPDATE")
        valid_content_new_and_update_mixedcase = valid_file_content.replace("new", "New").replace("update", "uPdAte")
        valid_content_new_and_delete_lowercase = valid_file_content.replace("update", "delete")
        valid_content_update_and_delete_lowercase = valid_file_content.replace("new", "delete").replace(
            "update", "UPDATE"
        )

        # Test case tuples are stuctured as (vaccine_type, vaccine_permissions, file_content, expected_result)
        test_cases = [
            # FLU, full permissions, lowercase action flags
            ("FLU", ["FLU_FULL"], valid_content_new_and_update_lowercase, True),
            # FLU, partial permissions, uppercase action flags
            ("FLU", ["FLU_CREATE"], valid_content_new_and_update_uppercase, True),
            # FLU, full permissions, mixed case action flags
            ("FLU", ["FLU_FULL"], valid_content_new_and_update_mixedcase, True),
            # FLU, partial permissions (create)
            ("FLU", ["FLU_DELETE", "FLU_CREATE"], valid_content_new_and_update_lowercase, True),
            # FLU, partial permissions (update)
            ("FLU", ["FLU_UPDATE"], valid_content_new_and_update_lowercase, True),
            # FLU, partial permissions (delete)
            ("FLU", ["FLU_DELETE"], valid_content_new_and_delete_lowercase, True),
            # FLU, no permissions
            ("FLU", ["FLU_UPDATE", "COVID19_FULL"], valid_content_new_and_delete_lowercase, False),
            # COVID19, full permissions
            ("COVID19", ["COVID19_FULL"], valid_content_new_and_delete_lowercase, True),
            # COVID19, partial permissions
            ("COVID19", ["COVID19_UPDATE"], valid_content_update_and_delete_lowercase, True),
            # COVID19, no permissions
            ("COVID19", ["FLU_CREATE", "FLU_UPDATE"], valid_content_update_and_delete_lowercase, False),
        ]

        for vaccine_type, vaccine_permissions, file_content, expected_result in test_cases:
            with self.subTest():
                with patch("src.initial_file_validation.get_supplier_permissions", return_value=vaccine_permissions):
                    # validate_action_flag_permissions takes a csv dict reader as one of it's args
                    csv_content_dict_reader = convert_string_to_dict_reader(file_content)
                    self.assertEqual(
                        validate_action_flag_permissions(csv_content_dict_reader, "TEST_SUPPLIER", vaccine_type),
                        expected_result,
                    )

    @mock_s3
    def test_initial_file_validation(self):
        """
        Tests that initial_file_validation returns True if all elements pass validation, and False otherwise
        """
        # Set up
        s3_client = boto3.client("s3", region_name="eu-west-2")
        s3_client.create_bucket(
            Bucket=self.test_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"}
        )
        valid_file_key = "Flu_Vaccinations_v5_YGA_20200101T12345600.csv"
        valid_file_content = Constants.valid_file_content

        # Test case tuples are stuctured as (file_key, file_content, expected_result)
        test_cases_for_full_permissions = [
            # Valid flu file key (mixed case)
            (valid_file_key, valid_file_content, True),
            # Valid covid19 file key (mixed case)
            (valid_file_key.replace("Flu", "Covid19"), valid_file_content, True),
            # Valid file key (all lowercase)
            (valid_file_key.lower(), valid_file_content, True),
            # Valid file key (all uppercase)
            # File key with no '.'
            (valid_file_key.replace(".", ""), valid_file_content, False),
            (valid_file_key.upper(), valid_file_content, True),
            # File key with additional '.'
            (valid_file_key[:2] + "." + valid_file_key[2:], valid_file_content, False),
            # File key with additional '_'
            (valid_file_key[:2] + "_" + valid_file_key[2:], valid_file_content, False),
            # File key with missing '_'
            (valid_file_key.replace("_", "", 1), valid_file_content, False),
            # File key with missing '_'
            (valid_file_key.replace("_", ""), valid_file_content, False),
            # File key with incorrect extension
            (valid_file_key.replace(".csv", ".dat"), valid_file_content, False),
            # File key with invalid vaccine type
            (valid_file_key.replace("Flu", "Flue"), valid_file_content, False),
            # File key with invalid vaccinations element
            (valid_file_key.replace("Vaccinations", "Vaccination"), valid_file_content, False),
            # File key with invalid version
            (valid_file_key.replace("v5", "v4"), valid_file_content, False),
            # File key with invalid ODS code
            (valid_file_key.replace("YGA", "YGAM"), valid_file_content, False),
            # File key with invalid timestamp
            (valid_file_key.replace("20200101T12345600", "20200132T12345600"), valid_file_content, False),
            # File with invalid content header
            (valid_file_key, valid_file_content.replace("PERSON_DOB", "PATIENT_DOB"), False),
        ]

        for file_key, file_content, expected_result in test_cases_for_full_permissions:
            with self.subTest():
                # Mock full permissions for the supplier (Note that YGA ODS code maps to the supplier 'TPP')
                with patch(
                    "src.initial_file_validation.get_permissions_config_json_from_s3",
                    return_value={"all_permissions": {"TPP": ["COVID19_FULL", "FLU_FULL"]}},
                ):
                    # Place the file in the bucket
                    s3_client.put_object(Bucket=self.test_bucket_name, Key=file_key, Body=file_content)
                    # Ensure that inital_file_validation passes or fails as expected
                    self.assertEqual(initial_file_validation(file_key, self.test_bucket_name), expected_result)

        # Test case tuples are stuctured as (file_key, file_content, expected_result)
        test_cases_for_partial_permissions = [
            # Has vaccine type and action flag permission
            (valid_file_key, valid_file_content, True),
            # Does not have vaccine type permission
            (valid_file_key.replace("Flu", "Covid19"), valid_file_content, False),
            # Has vaccine type permission, but not action flag permission
            (valid_file_key, valid_file_content.replace("new", "delete"), False),
        ]

        for file_key, file_content, expected_result in test_cases_for_partial_permissions:
            with self.subTest():
                # Mock full permissions for the supplier (Note that YGA ODS code maps to the supplier 'TPP')
                with patch(
                    "src.initial_file_validation.get_permissions_config_json_from_s3",
                    return_value={"all_permissions": {"TPP": ["FLU_CREATE"]}},
                ):
                    # Place the file in the bucket
                    s3_client.put_object(Bucket=self.test_bucket_name, Key=file_key, Body=file_content)
                    # Ensure that inital_file_validation passes or fails as expected
                    self.assertEqual(initial_file_validation(file_key, self.test_bucket_name), expected_result)