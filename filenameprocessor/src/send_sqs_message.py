"""Functions to send a message to SQS"""

import logging
import os
from json import dumps as json_dumps
from constants import Constants
from utils_for_filenameprocessor import extract_file_key_elements
from s3_clients import sqs_client

logger = logging.getLogger()


def send_to_supplier_queue(message_body: dict) -> bool:
    """Sends a message to the supplier queue and returns a bool indicating if the message has been successfully sent"""
    # Check the supplier has been identified (this should already have been validated by initial file validation)
    if not (supplier := message_body["supplier"]):
        logger.error("Message not sent to supplier queue as unable to identify supplier")
        return False

    # Find the URL of the relevant queue
    imms_env = os.getenv("SHORT_QUEUE_PREFIX", "imms-batch-internal-dev")
    supplier_sqs_name = Constants.SUPPLIER_TO_SQSQUEUE_MAPPINGS.get(supplier, supplier)
    account_id = os.getenv("PROD_ACCOUNT_ID") if "prod" in imms_env else os.getenv("LOCAL_ACCOUNT_ID")
    queue_url = f"https://sqs.eu-west-2.amazonaws.com/{account_id}/{imms_env}-metadata-queue.fifo"

    # Send to queue
    try:
        print("sqs_send_message going to initiate")
        sqs_client.send_message(QueueUrl=queue_url, MessageBody=json_dumps(message_body),
                                MessageDeduplicationId='1', MessageGroupId=supplier)
        print("Message sent to SQS queue '%s' for supplier %s", supplier_sqs_name, supplier)
    except sqs_client.exceptions.QueueDoesNotExist:
        logger.error("Failed to send message because queue %s does not exist", queue_url)
        return False
    except sqs_client.exceptions.InvalidMessageContents:
        logger.error("Failed to send message because the message contents are invalid")
        return False
    except sqs_client.exceptions.UnsupportedOperation:
        logger.error("Failed to send message because the operation is unsupported on the queue %s", queue_url)
        return False
    except sqs_client.exceptions.MessageTooLong:
        logger.error("Failed to send message because the message is too long for queue %s", queue_url)
        return False
    except sqs_client.exceptions.InvalidParameterValue as e:
        logger.error("Invalid parameter value: %s", e)
        return False
    except sqs_client.exceptions.RequestThrottled:
        logger.error("Request throttled when trying to send message to queue %s", queue_url)
        return False
    except sqs_client.exceptions.AWSSimpleQueueServiceException as e:
        logger.error("An AWS SQS exception occurred: %s", e)
        return False
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
        return False
    return True


def make_message_body_for_sqs(file_key: str, message_id: str) -> dict:
    """Returns the message body for the message which will be sent to SQS"""
    file_key_elements = extract_file_key_elements(file_key)
    return {
        "message_id": message_id,
        "vaccine_type": file_key_elements["vaccine_type"],
        "supplier": file_key_elements["supplier"],
        "timestamp": file_key_elements["timestamp"],
        "filename": file_key,
    }


def make_and_send_sqs_message(file_key: str, message_id: str) -> bool:
    """
    Attempts to send a message to the SQS queue.
    Returns a bool to indication if the message has been sent successfully.
    """
    message_body = make_message_body_for_sqs(file_key=file_key, message_id=message_id)
    print(f"message_body:{message_body}")
    return send_to_supplier_queue(message_body)
