import redis
import os
import logging
import json
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# Initialize Redis connection
redis_client = redis.StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)

file_key = "permissions_config.json"


def get_permissions_config_json_from_cache():
    """
    get the file content from ElastiCache.
    """
    # Get file content from cache
    print("fetch_from_elasticache process started")
    content = redis_client.get(file_key)
    print(f"content: {content}")
    json_content = json.loads(content)
    print(f"fetching: {json_content} successfully retrived from ElastiCache.")
    print("Permissions config json data retrieved")
    return json_content
