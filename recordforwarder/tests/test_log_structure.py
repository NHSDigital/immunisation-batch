"""Tests for Splunk logging"""

import unittest
from unittest.mock import patch
import json
from copy import deepcopy
from datetime import datetime
from contextlib import contextmanager, ExitStack
from send_request_to_lambda import send_request_to_lambda
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import Message
from errors import MessageNotSuccessfulError

FIXED_DATETIME = datetime(2024, 10, 30, 12, 0, 0)


class TestSplunkLogging(unittest.TestCase):
    """Tests for Splunk logging"""

    log_json_base = {
        "function_name": "send_request_to_lambda",
        "date_time": FIXED_DATETIME.strftime("%Y-%m-%d %H:%M:%S"),
        "supplier": "EMIS",
        "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
        "vaccine_type": "FLU",
        "message_id": "123456",
        "action_flag": "each test replaces this with the relevant action flag",
    }

    expected_log_json_success = {**log_json_base, "status": "success", "time_taken": "1.0s"}

    expected_log_json_failure = {**log_json_base, "status": "Fail", "time_taken": "1.0s", "status_code": 400}

    def extract_log_json(self, log: str) -> dict:
        """Extracts JSON from log entry."""
        log_entry = log.output[0]
        json_start = log_entry.find("{")
        json_end = log_entry.find("}")
        json_str = log_entry[json_start : json_end + 1]
        return json.loads(json_str)

    def make_log_assertions(self, log, mock_firehose_logger, operation: str, expected_error=None):
        """Assert that the log_json is as expected, and that the firehose logger was called with the log_json"""
        # Extract log_json
        self.assertGreater(len(log.output), 0)
        log_json = self.extract_log_json(log)

        # Prepare expected_log_json
        expected_log_json = (
            deepcopy(self.expected_log_json_success) if not expected_error else deepcopy(self.expected_log_json_failure)
        )
        expected_log_json["action_flag"] = operation.upper()
        expected_log_json.update({"error": expected_error} if expected_error else {})

        self.assertEqual(log_json, expected_log_json)

        mock_firehose_logger.forwarder_send_log.assert_called_once_with({"event": log_json})
        mock_firehose_logger.forwarder_send_log.reset_mock()

    @contextmanager
    def common_contexts_for_splunk_logging_tests(self):
        """
        A context manager which applies common patching for the tests in the TestSplunkLogging class.
        Yields mock_firehose_logger and logs (where logs is a list of the captured log entries).
        """
        with ExitStack() as stack:
            stack.enter_context(patch("time.time", side_effect=(1000000.0, 1000001.0, 1000003.0)))  # (start, end, ???)
            stack.enter_context(patch("log_structure.datetime"))
            stack.enter_context(patch("log_structure.datetime.now", return_value=FIXED_DATETIME))
            mock_firehose_logger = stack.enter_context(patch("log_structure.firehose_logger"))
            logs = stack.enter_context(self.assertLogs(level="INFO"))
            yield mock_firehose_logger, logs

    def test_splunk_logging_success(self):
        """Tests successful rows"""
        for operation in ["CREATE", "UPDATE", "DELETE"]:
            with self.subTest(operation):
                with (
                    self.common_contexts_for_splunk_logging_tests() as (mock_firehose_logger, logs),
                    patch(f"send_request_to_lambda.send_{operation.lower()}_request", return_value=Message.IMMS_ID),
                ):
                    message_body = {**Message.base_message_fields, "operation_requested": operation, "fhir_json": {}}
                    result = send_request_to_lambda(message_body)

                self.assertEqual(result, Message.IMMS_ID)
                self.make_log_assertions(logs, mock_firehose_logger, operation)

    def test_splunk_logging_failure_during_processing(self):
        """Tests a row which failed processing (and therefore has diagnostics in the message recevied from kinesis)"""
        diagnostics = "Unable to obtain IMMS ID"
        operation = "UPDATE"
        with (
            self.common_contexts_for_splunk_logging_tests() as (mock_firehose_logger, logs),
            self.assertRaises(MessageNotSuccessfulError) as context,
        ):
            message_body = {**Message.base_message_fields, "operation_requested": operation, "diagnostics": diagnostics}
            send_request_to_lambda(message_body)

        self.assertEqual(str(context.exception), diagnostics)
        self.make_log_assertions(logs, mock_firehose_logger, operation, expected_error=diagnostics)

    def test_splunk_logging_failure_during_forwarding(self):
        """Tests rows which fail during forwarding"""

        for operation in ["CREATE", "UPDATE", "DELETE"]:
            error_message = f"API Error: Unable to {operation.lower()} resource"
            with self.subTest(operation):
                with (
                    self.common_contexts_for_splunk_logging_tests() as (mock_firehose_logger, logs),
                    self.assertRaises(MessageNotSuccessfulError) as context,
                    patch(
                        f"send_request_to_lambda.send_{operation.lower()}_request",
                        side_effect=MessageNotSuccessfulError(error_message),
                    ),
                ):
                    message_body = {**Message.base_message_fields, "operation_requested": operation, "fhir_json": {}}
                    send_request_to_lambda(message_body)

                self.assertEqual(str(context.exception), error_message)
                self.make_log_assertions(logs, mock_firehose_logger, operation, expected_error=error_message)
