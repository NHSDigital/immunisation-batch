"""
Lambda function for the fileprocessor lambda.
NOTE: The expected file format for the incoming file is 'VACCINETYPE_Vaccinations_version_ODSCODE_DATETIME.csv'.
e.g. 'Flu_Vaccinations_v5_YYY78_20240708T12130100.csv' (ODS code has multiple lengths)
"""

from json import dumps as json_dumps
import logging
from uuid import uuid4
from initial_file_validation import initial_file_validation
from send_sqs_message import make_and_send_sqs_message
from make_and_upload_ack_file import make_and_upload_ack_file
from s3_clients import s3_client
from elasticcache import upload_to_elasticache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def lambda_handler(event, context):  # pylint: disable=unused-argument
    """Lambda handler for filenameprocessor lambda"""

    error_files = []

    # For each file
    for record in event["Records"]:
        try:
            # Assign a unique message_id for the file
            message_id = str(uuid4())
            created_at_formatted_string = None
            # Obtain the file details
            bucket_name = record["s3"]["bucket"]["name"]
            print(f"bucket_name:{bucket_name}")
            file_key = record["s3"]["object"]["key"]
            print(f"file_key:{file_key}")
            response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
            print(f"response:{response}")
            created_at_formatted_string = response["LastModified"].strftime("%Y%m%dT%H%M%S00")

            # Process the file
            if "data-sources" in bucket_name:
                # Process file from batch_data_source_bucket with validation
                print("source upload initiated started")
                validation_passed, permission = initial_file_validation(file_key, bucket_name)
                print(f"validation_passed:{validation_passed}")
                message_delivered = make_and_send_sqs_message(file_key,
                                                              message_id, permission) if validation_passed else False
                print(f"message_delivered:{message_delivered}")
                make_and_upload_ack_file(
                    message_id, file_key, validation_passed, message_delivered, created_at_formatted_string
                )
            elif "configs" in bucket_name:
                # For files in batch_config_bucket, upload to ElastiCache
                print("cache upload initiated started")
                logger.info("cache upload initiated started")
                try:
                    upload_to_elasticache(file_key, bucket_name)
                except Exception as cache_error:
                    # Handle ElastiCache-specific errors
                    print(f"Error uploading to ElastiCache for file '{file_key}': {cache_error}")
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
    if "configs" in bucket_name:
        logger.info("The upload of file content from the S3 bucket to the cache has been successfully completed")
        return {"statusCode": 200, "body": json_dumps("File content upload to cache from S3 bucket completed")}
    else:
        logger.info("Completed processing all file metadata in current batch")
        return {"statusCode": 200, "body": json_dumps("File processing for S3 bucket completed")}
