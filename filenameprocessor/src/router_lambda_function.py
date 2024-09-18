"""
Lambda function for the fileprocessor lambda.
NOTE: The expected file format for the incoming file is 'VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv'.
e.g. 'Flu_Vaccinations_v5_YYY78_20240708T12130100.csv' (ODS code has multiple lengths)
"""

import json
import logging
import uuid
import boto3
from initial_file_validation import initial_file_validation
from send_to_supplier_queue import try_to_send_message
from create_ack_file import create_ack_file


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Lambda handler for filenameprocessor lambda"""
    # Set up S3 and SQS clients
    s3_client = boto3.client("s3", region_name="eu-west-2")
    sqs_client = boto3.client("sqs", region_name="eu-west-2")

    error_files = []

    # For each file
    for record in event["Records"]:

        # Assign a unique message_id
        message_id = str(uuid.uuid4())

        # Obtain the file details
        bucket_name = record["s3"]["bucket"]["name"]
        file_key = record["s3"]["object"]["key"]
        response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        created_at_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

        try:
            # Validate the file
            validation_passed = initial_file_validation(file_key, bucket_name, s3_client)

            # If file is valid then send a message to the SQS queue
            message_delivered = try_to_send_message(file_key, message_id, sqs_client) if validation_passed else False

        except Exception as e:
            logging.error("Error processing file'%s': %s", file_key, str(e))
            validation_passed = False
            message_delivered = False
            error_files.append(file_key)

        create_ack_file(message_id, file_key, validation_passed, message_delivered, created_at_string, s3_client)

    if error_files:
        logger.error("Processing errors occurred for the following files: %s", ", ".join(error_files))

    logger.info("Completed processing all file metadata in current batch")
    return {"statusCode": 200, "body": json.dumps("File processing for S3 bucket completed")}
