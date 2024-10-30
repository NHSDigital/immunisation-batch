"""Function to send the message to kinesis"""

import os
import logging
import simplejson as json
from botocore.exceptions import ClientError
from s3_clients import kinesis_client

logger = logging.getLogger()


def send_to_kinesis(supplier: str, message_body: dict) -> bool:
    """Send a message to the specified Kinesis stream. Returns a boolean indicating whether the send was successful."""
    try:
        stream_name = f"{os.getenv('SHORT_QUEUE_PREFIX', 'imms-batch-internal-dev')}-processingdata-stream"
        data = json.dumps(message_body, ensure_ascii=False)
        stream_arn = os.getenv("KINESIS_STREAM_ARN")
        resp = kinesis_client.put_record(StreamName=stream_name, StreamARN=stream_arn, Data=data, PartitionKey=supplier)
        logger.info("Message sent to Kinesis stream: %s for supplier: %s with resp: %s", stream_name, supplier, resp)
        return True
    except ClientError as error:
        logger.error("Error sending message to Kinesis: %s", error)
        return False
