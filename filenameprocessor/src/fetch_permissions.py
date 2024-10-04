import redis
import boto3
import os
import logging
import json
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# Initialize Redis connection
redis_client = redis.StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)
s3_client = boto3.client('s3')
file_key = "permissions_config.json"


def get_permissions_config_json_from_cache():
    """
    Uploads the file content from S3 to ElastiCache (Redis).
    """
    # Get file content from cache
    print("fetch_from_elasticache process started")
    content = redis_client.get(file_key)
    print(f"content: {content}")
    json_content = json.loads(content)
    print(f"fetching: {json_content} successfully retrived from ElastiCache.")
    print("Permissions config json data retrieved")
    return json_content
