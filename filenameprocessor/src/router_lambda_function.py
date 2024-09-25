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
from send_sqs_message import make_and_send_sqs_message
from make_and_upload_ack_file import make_and_upload_ack_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

s3_client = boto3.client("s3", region_name="eu-west-2")


def lambda_handler(event, context):  # pylint: disable=unused-argument
    """Lambda handler for filenameprocessor lambda"""
    error_files = []

    # For each file
    for record in event["Records"]:
        try:
            # Assign a unique message_id for the file
            message_id = str(uuid.uuid4())

            # Obtain the file details
            bucket_name = record["s3"]["bucket"]["name"]
            file_key = record["s3"]["object"]["key"]
            response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
            created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

            # Process the file
            validation_passed = initial_file_validation(file_key, bucket_name)
            message_delivered = make_and_send_sqs_message(file_key, message_id) if validation_passed else False
            make_and_upload_ack_file(
                message_id, file_key, validation_passed, message_delivered, created_at_formatted_string
            )

        except Exception as error:  # pylint: disable=broad-except
            # If an unexpected error occured, add the file to the error_files list, and upload an ack file
            message_id = message_id or "Message id was not created"
            file_key = file_key or "Unable to identify file key"
            validation_passed = False
            message_delivered = False
            created_at_formatted_string = created_at_formatted_string or "Unable to identify or format created at time"
            logging.error("Error processing file'%s': %s", file_key, str(error))
            error_files.append(file_key)
            make_and_upload_ack_file(
                message_id, file_key, validation_passed, message_delivered, created_at_formatted_string
            )

    if error_files:
        logger.error("Processing errors occurred for the following files: %s", ", ".join(error_files))

    logger.info("Completed processing all file metadata in current batch")
    return {"statusCode": 200, "body": json.dumps("File processing for S3 bucket completed")}
