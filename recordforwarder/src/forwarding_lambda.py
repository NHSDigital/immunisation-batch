"""Functions for forwarding each row to the Imms API"""

import json
import base64
import logging
from update_ack_file import update_ack_file
from send_request_to_api import send_request_to_api
from errors import MessageNotSuccessfulError

logging.basicConfig(level="INFO")
logger = logging.getLogger()


def forward_request_to_api(message_body):
    """Forwards the request to the Imms API (where possible) and updates the ack file with the outcome"""
    file_key = message_body.get("file_key")
    row_id = message_body.get("row_id")
    logger.info("BEGINNIING FORWARDING MESSAGE: ID %s", row_id)
    try:
        imms_id = send_request_to_api(message_body)
        update_ack_file(file_key, row_id, successful_api_response=True, diagnostics=None, imms_id=imms_id)
    except MessageNotSuccessfulError as error:
        imms_id = message_body.get("imms_id")  # imms_id may already have been identified in recordprocessing
        update_ack_file(file_key, row_id, successful_api_response=False, diagnostics=error.message, imms_id=imms_id)
    logger.info("FINISHED FORWARDING MESSAGE: ID %s", row_id)


def forward_lambda_handler(event, _):
    """Forward each row to the Imms API"""
    logger.info("Processing started")
    for record in event["Records"]:
        try:
            kinesis_payload = record["kinesis"]["data"]
            decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
            message_body = json.loads(decoded_payload)
            forward_request_to_api(message_body)
        except Exception as error:  # pylint:disable=broad-exception-caught
            logger.error("Error processing message: %s", error)
    logger.info("Processing ended")


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
