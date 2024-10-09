"""Function to send the message to kinesis"""

import os
import json
import logging
from botocore.exceptions import ClientError
from s3_clients import kinesis_client

logger = logging.getLogger()


def send_to_kinesis(supplier, message_body):
    """Send a message to the specified Kinesis stream. Returns a boolean indicating whether the send was successful."""
    try:
        kinesis_queue_prefix = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")
        stream_name = f"{kinesis_queue_prefix}-processingdata-stream"
        data = json.dumps(message_body, ensure_ascii=False)
        stream_arn = os.getenv("KINESIS_STREAM_ARN")
        resp = kinesis_client.put_record(StreamName=stream_name, StreamARN=stream_arn, Data=data, PartitionKey=supplier)
        logger.info("Message sent to Kinesis stream:%s for supplier:%s with resp:%s", stream_name, supplier, resp)
        return True
    except ClientError as error:
        logger.error("Error sending message to Kinesis: %s", error)
        return False
