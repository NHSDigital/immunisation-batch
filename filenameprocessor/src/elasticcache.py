import redis
import boto3
import os
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


# Initialize Redis connection
redis_client = redis.StrictRedis(host=os.getenv('REDIS_HOST'), port=os.getenv('REDIS_PORT'), decode_responses=True)
s3_client = boto3.client('s3')


def upload_to_elasticache(file_key, bucket_name):
    """
    Uploads the file content from S3 to ElastiCache (Redis).
    """
    # Get file content from S3
    print("upload_to_elasticache process started")
    response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
    print(f"response_upload:{response}")
    file_content = response['Body'].read().decode('utf-8')
    print(f"file_content:{file_content}")
    # Use the file_key as the Redis key and file content as the value
    redis_client.set(file_key, file_content)
    print(f"File {file_key} successfully uploaded to ElastiCache.")