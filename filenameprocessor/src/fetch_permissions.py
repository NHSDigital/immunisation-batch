import boto3
import json

# from datetime import datetime

# Global variables to hold the cached JSON data and its last modified time
_CACHED_JSON_DATA = None
_CACHED_LAST_MODIFIED = None

JSON_FILE_KEY = "permissions_config.json"


def get_permissions_config_json_from_s3(config_bucket_name):
    global _CACHED_JSON_DATA, _CACHED_LAST_MODIFIED

    s3 = boto3.client("s3", region_name="eu-west-2")

    try:
        # Fetch the file's metadata to get the LastModified time
        response = s3.head_object(Bucket=config_bucket_name, Key=JSON_FILE_KEY)
        last_modified = response["LastModified"]

        # Reload the JSON if the file has been modified
        if _CACHED_LAST_MODIFIED is None or last_modified > _CACHED_LAST_MODIFIED:
            print("Fetching updated JSON from S3...")
            response = s3.get_object(Bucket=config_bucket_name, Key=JSON_FILE_KEY)
            json_content = response["Body"].read().decode("utf-8")
            _CACHED_JSON_DATA = json.loads(json_content)
            _CACHED_LAST_MODIFIED = last_modified
            print(f"CACHED_JSON:{_CACHED_JSON_DATA}")
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return {}

    return _CACHED_JSON_DATA
