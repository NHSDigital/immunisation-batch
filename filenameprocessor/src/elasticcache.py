import redis
import boto3
import os
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Initialize Redis connection with timeout
redis_client = redis.StrictRedis(
    host=os.getenv('REDIS_HOST'),
    port=os.getenv('REDIS_PORT'),
    socket_timeout=10,  # Set a 5-second timeout for connection
    decode_responses=True
)
print(f"redis_client:{redis_client}")
s3_client = boto3.client('s3')


def retry_redis_set(file_key, file_content, retries=3, delay=2):
    """
    Tries to upload the content to Redis with retries on failure.
    """
    for attempt in range(retries):
        try:
            redis_client.set(file_key, file_content)
            print(f"File {file_key} successfully uploaded to ElastiCache.")
            break
        except redis.RedisError as e:
            if attempt < retries - 1:
                print(f"Retrying Redis connection. Attempt {attempt + 1}/{retries}")
                time.sleep(delay)
            else:
                logger.error(f"Failed to upload {file_key} to ElastiCache after {retries} attempts: {str(e)}")


def upload_to_elasticache(file_key, bucket_name):
    """
    Uploads the file content from S3 to ElastiCache (Redis) with retry logic.
    """
    try:
        print("upload_to_elasticache process started")

        # Get file content from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        print(f"S3 response: {response}")

        file_content = response['Body'].read().decode('utf-8')
        print(f"File content fetched from S3 for key {file_key}: {file_content}")

        # Try setting the value in Redis with retries
        retry_redis_set(file_key, file_content)
        test_redis_connection()

    except boto3.exceptions.Boto3Error as e:
        logger.error(f"Error fetching file {file_key} from S3: {str(e)}")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")


def test_redis_connection():
    try:
        redis_client.ping()
        print("Successfully connected to Redis.")
    except redis.ConnectionError as e:
        print(f"Failed to connect to Redis: {str(e)}")
