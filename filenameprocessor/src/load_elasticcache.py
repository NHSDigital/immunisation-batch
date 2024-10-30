import redis
from boto_clients import s3_client
from decrpyt_key import decrypt_key


def upload_to_elasticache(file_key, bucket_name):
    """
    Uploads the file content from S3 to ElastiCache (Redis).
    """
    host_addr = decrypt_key('REDIS_HOST')
    port_no = decrypt_key('REDIS_PORT')
    redis_client = redis.StrictRedis(host=host_addr, port=port_no, decode_responses=True)
    # Get file content from S3
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    file_content = response['Body'].read().decode('utf-8')
    # Use the file_key as the Redis key and file content as the value
    redis_client.set(file_key, file_content)
