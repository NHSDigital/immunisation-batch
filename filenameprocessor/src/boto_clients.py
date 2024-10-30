"""Initialise s3 and sqs clients"""

from boto3 import client as boto3_client

s3_client = boto3_client("s3", region_name="eu-west-2")
sqs_client = boto3_client("sqs", region_name="eu-west-2")
kms_client = boto3_client('kms')
