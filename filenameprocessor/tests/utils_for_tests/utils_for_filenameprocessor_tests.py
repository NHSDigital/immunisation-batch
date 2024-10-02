# """Utils functions for filenameprocessor tests"""

# from os import path
# from io import StringIO
# from csv import reader, DictReader
# from boto3 import client as boto3_client
# from tests.utils_for_tests.values_for_tests import VALID_FILE_CONTENT


# def setup_s3_bucket_and_file(
#     test_bucket_name: str, test_file_key: str, test_file_content: str = VALID_FILE_CONTENT
# ) -> None:
#     """
#     Sets up the S3 client and uploads the test file, containing the test file content, to a bucket named 'test_bucket'
#     """
#     s3_client = boto3_client("s3", region_name="eu-west-2")
#     s3_client.create_bucket(Bucket=test_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
#     s3_client.put_object(Bucket=test_bucket_name, Key=test_file_key, Body=test_file_content)


# def convert_csv_to_string(filename):
#     """Open a csv file and return the file content as a string"""
#     file_path = f"{path.dirname(path.abspath(__file__))}/{filename}"
#     with open(file_path, mode="r", encoding="utf-8") as file:
#         return "".join(file.readlines())


# def convert_csv_to_reader(filename):
#     """Open a csv file and return the file content as a csv reader"""
#     file_path = f"{path.dirname(path.abspath(__file__))}/{filename}"
#     with open(file_path, mode="r", encoding="utf-8") as file:
#         data = file.read()
#     return reader(StringIO(data), delimiter="|")


# def convert_string_to_dict_reader(data_string: str):
#     """Take a data string and convert it to a csv DictReader"""
#     return DictReader(StringIO(data_string), delimiter="|")
