import redis
import json
from decrpyt_key import decrypt_key


file_key = "permissions_config.json"


def get_permissions_config_json_from_cache():
    """
    get the file content from ElastiCache.
    """
    host_addr = decrypt_key('REDIS_HOST')
    port_no = decrypt_key('REDIS_PORT')
    redis_client = redis.StrictRedis(host=host_addr, port=port_no, decode_responses=True)
    # Get file content from cache
    content = redis_client.get(file_key)
    json_content = json.loads(content)
    return json_content
