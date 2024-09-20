"""Utils functions for filenameprocessor tests"""

import boto3
from src.constants import Constants


def setup_s3_bucket_and_file(test_bucket_name, test_file_key, test_file_content=Constants.valid_file_content):
    """
    Sets up the S3 client and uploads the test file, containing the test file content, to a bucket named
    'test_bucket'. Returns the S3 client
    """
    s3_client = boto3.client("s3", region_name="eu-west-2")
    s3_client.create_bucket(Bucket=test_bucket_name, CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})
    s3_client.put_object(Bucket=test_bucket_name, Key=test_file_key, Body=test_file_content)
    return s3_client
