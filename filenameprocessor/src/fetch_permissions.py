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
    content = redis_client.get(file_key)
    json_content = json.loads(content)
    return json_content
