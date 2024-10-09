"""Utils for filenameprocessor lambda"""

import os
from csv import DictReader
from io import StringIO
from s3_clients import s3_client


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def fetch_file_from_s3(bucket_name, file_key):
    """Returns the requested file contents in the form of a DictReader"""
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_data = response["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_data), delimiter="|")


def get_csv_content_dict_reader(bucket_name: str, file_key: str):
    """Downloads the csv data and returns a csv_reader with the content of the csv"""
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")
