import boto3
import json

# from datetime import datetime

# Global variables to hold the cached JSON data and its last modified time
_cached_json_data = None
_cached_last_modified = None

json_file_key = "permissions_config.json"


def get_json_from_s3(bucket_name):
    global _cached_json_data, _cached_last_modified

    s3 = boto3.client("s3", region_name="eu-west-2")

    try:
        # Fetch the file's metadata to get the LastModified time
        response = s3.head_object(Bucket=bucket_name, Key=json_file_key)
        last_modified = response["LastModified"]

        # Reload the JSON if the file has been modified
        if _cached_last_modified is None or last_modified > _cached_last_modified:
            print("Fetching updated JSON from S3...")
            response = s3.get_object(Bucket=bucket_name, Key=json_file_key)
            json_content = response["Body"].read().decode("utf-8")
            _cached_json_data = json.loads(json_content)
            _cached_last_modified = last_modified
            print(f"CACHED_JSON:{_cached_json_data}")
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None

    return _cached_json_data
