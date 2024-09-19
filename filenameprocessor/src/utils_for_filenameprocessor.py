"""Utils for filenameprocessor lambda"""

import os
import csv
from typing import Union
from io import StringIO
from constants import Constants


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def get_csv_content_dict_reader(bucket_name: str, file_key: str, s3_client):
    """Downloads the csv data and returns a csv_reader with the content of the csv"""
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = csv_obj["Body"].read().decode("utf-8")
    return csv.DictReader(StringIO(csv_content_string), delimiter="|")


def identify_supplier(ods_code: str) -> Union[str, None]:
    """Identify the supplier from the ods code using the mapping"""
    return Constants.ODS_TO_SUPPLIER_MAPPINGS.get(ods_code)


def extract_file_key_elements(file_key: str) -> dict:
    """Returns a dictionary containing each of the elements which can be extracted from the file key"""
    file_key_parts_without_extension = file_key.split(".")[0].split("_")
    file_key_elements = {
        "vaccine_type": file_key_parts_without_extension[0].upper(),
        "vaccination": file_key_parts_without_extension[1].lower(),
        "version": file_key_parts_without_extension[2].lower(),
        "ods_code": file_key_parts_without_extension[3],
        "timestamp": file_key_parts_without_extension[4],
        "extension": file_key.split(".")[1],
    }
    # Identify the supplier using the ODS code (defaults to None if ODS code not found) and add to file_key_elements
    file_key_elements["supplier"] = identify_supplier(file_key_elements["ods_code"])
    return file_key_elements
