import logging
import json
import os
from clients import firehose_client

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel("INFO")

DELIVERY_STREAM_NAME = os.getenv("SPLUNK_FIREHOSE_NAME")


class Forwarder_FirehoseLogger:

    def forwarder_send_log(self, log_message):
        try:
            response = firehose_client.put_record(
                DeliveryStreamName=DELIVERY_STREAM_NAME, Record={"Data": json.dumps(log_message).encode("utf-8")}
            )
            logger.info("Log sent to Firehose: %s", response)
        except Exception as error:  # pylint: disable=broad-exception-caught
            logger.exception("Error sending log to Firehose: %s", error)
