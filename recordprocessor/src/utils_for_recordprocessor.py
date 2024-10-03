"""Utils for filenameprocessor lambda"""

import os
from csv import DictReader
from typing import Union
from io import StringIO
from constants import Constants
from s3_clients import s3_client


def get_environment() -> str:
    """Returns the current environment. Defaults to internal-dev for pr and user environments"""
    _env = os.getenv("ENVIRONMENT")
    # default to internal-dev for pr and user environments
    return _env if _env in ["internal-dev", "int", "ref", "sandbox", "prod"] else "internal-dev"


def get_csv_content_dict_reader(bucket_name: str, file_key: str):
    """Downloads the csv data and returns a csv_reader with the content of the csv"""
    csv_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    csv_content_string = csv_obj["Body"].read().decode("utf-8")
    return DictReader(StringIO(csv_content_string), delimiter="|")


# def identify_supplier(ods_code: str) -> Union[str, None]:
#     """
#     Identifies the supplier from the ods code using the mapping.
#     Defaults to empty string if ODS code isn't found in the mappings
#     """
#     return Constants.ODS_TO_SUPPLIER_MAPPINGS.get(ods_code, "")


def extract_file_key_elements(file_key: str) -> dict:
    """
    Returns a dictionary containing each of the elements which can be extracted from the file key.
    All elements are converted to upper case.\n
    Supplier is identified using the ods_to_supplier mapping and defaulted to empty string if ODS code is not found.\n
    NOTE: This function works on the assumption that the file_key has already
    been validated as having four underscores and a single '.' which occurs after the four of the underscores.
    """
    file_key = file_key.upper()
    file_key_parts_without_extension = file_key.split(".")[0].split("_")
    file_key_elements = {
        "vaccine_type": file_key_parts_without_extension[0],
        "vaccination": file_key_parts_without_extension[1],
        "version": file_key_parts_without_extension[2],
        "ods_code": file_key_parts_without_extension[3],
        "timestamp": file_key_parts_without_extension[4],
        "extension": file_key.split(".")[1],
    }

    # Identify the supplier using the ODS code (defaults to empty string if ODS code not found)
    file_key_elements["supplier"] = identify_supplier(file_key_elements["ods_code"])

    return file_key_elements
