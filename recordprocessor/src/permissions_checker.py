import json
import logging
import os
from utils_for_recordprocessor import get_environment
from s3_clients import s3_client

logger = logging.getLogger()

# Global variables to hold the cached JSON data and its last modified time
__CACHED_JSON_DATA = None
_CACHED_LAST_MODIFIED = None

JSON_FILE_KEY = "permissions_config.json"


def get_permissions_config_json_from_s3():
    global __CACHED_JSON_DATA, _CACHED_LAST_MODIFIED  # pylint: disable=global-statement

    try:
        # Fetch the file's metadata to get the LastModified time
        config_bucket_name = os.getenv("CONFIG_BUCKET_NAME", f"immunisation-batch-{get_environment()}-configs")
        last_modified = s3_client.head_object(Bucket=config_bucket_name, Key=JSON_FILE_KEY)["LastModified"]

        # Reload the JSON if the file has been modified
        if _CACHED_LAST_MODIFIED is None or last_modified > _CACHED_LAST_MODIFIED:
            response = s3_client.get_object(Bucket=config_bucket_name, Key=JSON_FILE_KEY)
            json_content = response["Body"].read().decode("utf-8")
            __CACHED_JSON_DATA = json.loads(json_content)
            _CACHED_LAST_MODIFIED = last_modified
    except Exception as error:  # pylint: disable=broad-exception-caught
        logger.info("Error loading JSON file: %s", error)
        return None

    return __CACHED_JSON_DATA
