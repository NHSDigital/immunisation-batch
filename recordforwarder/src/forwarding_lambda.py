"""Functions for forwarding each row to the Imms API"""

import os
import json
import base64
import logging
from send_request_to_lambda import send_request_to_lambda
from errors import MessageNotSuccessfulError
from clients import sqs_client

logging.basicConfig(level="INFO")
logger = logging.getLogger()

queue_url = os.getenv("SQS_QUEUE_URL", "Queue_url")


def forward_request_to_lambda(message_body):
    """Forwards the request to the Imms API (where possible) and updates the ack file with the outcome"""
    row_id = message_body.get("row_id")
    logger.info("BEGINNING FORWARDING MESSAGE: ID %s", row_id)
    try:
        send_request_to_lambda(message_body)
    except MessageNotSuccessfulError as error:
        error_message_body = {
            "diagnostics": str(error.message),
            "supplier": message_body.get("supplier"),
            "file_key": message_body.get("file_key"),
            "row_id": message_body.get("row_id"),
            "created_at_formatted_string":  message_body.get("created_at_formatted_string"),
        }
        sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(error_message_body),
            MessageGroupId=error_message_body["file_key"],
        )
        logger.info("Error: %s", error)
    logger.info("FINISHED FORWARDING MESSAGE: ID %s", row_id)


def forward_lambda_handler(event, _):
    """Forward each row to the Imms API"""
    logger.info("Processing started")
    for record in event["Records"]:
        try:
            kinesis_payload = record["kinesis"]["data"]
            decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
            message_body = json.loads(decoded_payload)
            forward_request_to_lambda(message_body)
        except Exception as error:  # pylint:disable=broad-exception-caught
            logger.error("Error processing message: %s", error)
    logger.info("Processing ended")


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
