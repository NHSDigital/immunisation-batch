import unittest
import os
import io
import csv
from unittest.mock import patch, MagicMock
from make_and_upload_ack_file import make_and_upload_ack_file


def convert_csv_to_string(filename):
    file_path = f"{os.path.dirname(os.path.abspath(__file__))}/{filename}"
    with open(file_path, mode="r", encoding="utf-8") as file:
        return "".join(file.readlines())


def convert_csv_to_reader(filename):
    file_path = f"{os.path.dirname(os.path.abspath(__file__))}/{filename}"
    with open(file_path, mode="r", encoding="utf-8") as file:
        data = file.read()
    return csv.reader(io.StringIO(data), delimiter="|")


def convert_string_to_dict_reader(data_string: str):
    return csv.DictReader(io.StringIO(data_string), delimiter="|")


class TestRouterLambdaFunctions(unittest.TestCase):
    def setUp(self):
        self.file_key = "Flu_Vaccinations_v5_YGM41_20240708T12130100.csv"
        self.bucket_name = "test-bucket"
        self.ods_code = "YGM41"
        self.mock_s3_client = MagicMock()
        self.mock_sqs_client = MagicMock()

    def test_make_and_upload_ack_file(self):
        """tests whether ack file is created"""
        validation_passed = True
        created_at_formatted = "20240725T12510700"
        s3_client = MagicMock()
        with patch("make_and_upload_ack_file.s3_client", s3_client):
            make_and_upload_ack_file("1", self.file_key, validation_passed, True, created_at_formatted)
        s3_client.upload_fileobj.assert_called_once()
