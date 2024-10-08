import json
import logging
import os
from utils_for_recordprocessor import get_environment
from s3_clients import s3_client

logger = logging.getLogger()

# Global variables to hold the cached JSON data and its last modified time
_cached_json_data = None
_cached_last_modified = None

json_file_key = "permissions_config.json"


def get_permissions_config_json_from_s3():
    global _cached_json_data, _cached_last_modified
    try:
        # Fetch the file's metadata to get the LastModified time
        config_bucket_name = os.getenv("CONFIG_BUCKET_NAME", f"immunisation-batch-{get_environment()}-configs")
        response = s3_client.head_object(Bucket=config_bucket_name, Key=json_file_key)
        last_modified = response["LastModified"]

        # Reload the JSON if the file has been modified
        if _cached_last_modified is None or last_modified > _cached_last_modified:
            response = s3_client.get_object(Bucket=config_bucket_name, Key=json_file_key)
            json_content = response["Body"].read().decode("utf-8")
            _cached_json_data = json.loads(json_content)
            _cached_last_modified = last_modified
    except Exception as e:
        logger.info(f"Error loading JSON file: {e}")
        return None

    return _cached_json_data
