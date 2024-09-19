"""Function to get the permissions_config.json file from S3 config buckets"""

import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global variables to hold the cached JSON data and its last modified time
_CACHED_JSON_DATA = None
_CACHED_LAST_MODIFIED = None

JSON_FILE_KEY = "permissions_config.json"


def get_permissions_config_json_from_s3(config_bucket_name) -> dict:
    """
    Returns the permissions config json, loaded from the permissions config file in the S3 config bucket.
    If an error occurs then the default return value is an empty dictionary.
    """
    global _CACHED_JSON_DATA, _CACHED_LAST_MODIFIED

    s3 = boto3.client("s3", region_name="eu-west-2")

    try:
        # Fetch the file's metadata to get the LastModified time
        response = s3.head_object(Bucket=config_bucket_name, Key=JSON_FILE_KEY)
        last_modified = response["LastModified"]

        # Reload the JSON if the file has been modified
        if _CACHED_LAST_MODIFIED is None or last_modified > _CACHED_LAST_MODIFIED:
            response = s3.get_object(Bucket=config_bucket_name, Key=JSON_FILE_KEY)
            json_content = response["Body"].read().decode("utf-8")
            _CACHED_JSON_DATA = json.loads(json_content)
            _CACHED_LAST_MODIFIED = last_modified
    except Exception as error:
        logger.error("Error loading permissions_config.json from config bucket: {%s}", error)
        return {}

    logger.info("Permissions config json data retrieved")
    return _CACHED_JSON_DATA
