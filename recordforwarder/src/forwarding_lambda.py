"""Functions for forwarding each row to the Imms API"""

import json
import base64
import logging
from update_ack_file import update_ack_file
from send_request_to_api import send_request_to_api

logger = logging.getLogger()


def forward_request_to_api(message_body):
    """Forwards the request to the Imms API (where possible) and updates the ack file with the outcome"""
    file_key = message_body.get("file_name")
    row_id = message_body.get("message_id")
    message_delivered, response_code, diagnostics = send_request_to_api(message_body)
    update_ack_file(file_key, row_id, message_delivered, response_code, diagnostics)


def forward_lambda_handler(event, _):
    """Forward each row to the Imms API"""
    for record in event["Records"]:
        try:
            kinesis_payload = record["kinesis"]["data"]
            decoded_payload = base64.b64decode(kinesis_payload).decode("utf-8")
            message_body = json.loads(decoded_payload)
            forward_request_to_api(message_body)
        except Exception as error:  # pylint:disable=broad-exception-caught
            logger.error("Error processing message: %s", error)


if __name__ == "__main__":
    forward_lambda_handler({"Records": []}, {})
