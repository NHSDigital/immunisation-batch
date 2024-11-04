"""Tests for Splunk logging"""

import unittest
from unittest.mock import patch
import json
from copy import deepcopy
from datetime import datetime
from send_request_to_lambda import send_request_to_lambda
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import Message
from errors import MessageNotSuccessfulError


class TestSplunkLogging(unittest.TestCase):
    """Tests for Splunk logging"""

    test_fixed_time_taken = [
        1000000.0,
        1000001.0,
        1000001.0,
        1000000.0,
        1000001.0,
        1000001.0,
        1000000.0,
        1000001.0,
        1000001.0,
    ]

    fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)

    example_diagnostics = "Unable to obtain IMMS ID"

    message_body_base = {
        "row_id": "6543219",
        "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
        "supplier": "EMIS",
        "operation_requested": "UPDATE",
    }

    log_json_base = {
        "function_name": "send_request_to_lambda",
        "date_time": fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "supplier": "EMIS",
        "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
        "vaccine_type": "FLU",
        "message_id": "6543219",
        "action_flag": "action_flag",
    }

    message_body_success = {**message_body_base, "fhir_json": {"resourceType": "Immunization"}}

    expected_log_json_success = {**log_json_base, "status": "success", "time_taken": 1.0}

    message_body_with_diagnostics = {**message_body_base, "diagnostics": example_diagnostics}

    expected_log_json_failure = {
        **log_json_base,
        "status": "Fail",
        "time_taken": "1.0s",
        "status_code": 400,
        "error": example_diagnostics,
    }

    def extract_log_json(self, log: str) -> dict:
        """Extracts JSON from log entry."""
        log_entry = log.output[0]
        json_start = log_entry.find("{")
        json_end = log_entry.find("}")
        json_str = log_entry[json_start : json_end + 1]
        return json.loads(json_str)

    def test_splunk_logging_success(self):
        """
        Test that for a successful row the log_json has all the expected keys and values, and the firehose logger
        is called with the log_json.
        """
        for operation in ["CREATE", "UPDATE", "DELETE"]:
            with self.subTest(operation):
                with (
                    self.subTest(operation),
                    self.assertLogs(level="INFO") as log,
                    patch("log_structure.firehose_logger") as mock_firehose_logger,
                    patch("time.time", side_effect=self.test_fixed_time_taken),
                    patch("log_structure.datetime") as mock_datetime,
                    patch(f"send_request_to_lambda.send_{operation.lower()}_request", return_value=Message.IMMS_ID),
                ):
                    mock_datetime.now.return_value = self.fixed_datetime

                    message_body = self.message_body_success.copy()
                    message_body["operation_requested"] = operation
                    result = send_request_to_lambda(message_body)

                self.assertEqual(result, Message.IMMS_ID)

                self.assertGreater(len(log.output), 0)
                log_json = self.extract_log_json(log)
                expected_log_json = deepcopy(self.expected_log_json_success)
                expected_log_json["action_flag"] = operation
                self.assertEqual(log_json, expected_log_json)
                self.assertIsInstance(log_json["time_taken"], float)

                mock_firehose_logger.forwarder_send_log.assert_called_once_with({"event": log_json})
                mock_firehose_logger.forwarder_send_log.reset_mock()

    def test_splunk_logging_failure_during_processing(self):
        """
        Test that for a row which failed processing (and therefore has diagnostics in the message recevied from
        kinesis), the log_json has all the expected keys and values, and the firehose logger is called with the
        log_json.
        """
        with (
            self.assertLogs(level="INFO") as log,
            self.assertRaises(MessageNotSuccessfulError) as context,
            patch("log_structure.firehose_logger") as mock_firehose_logger,
            patch("time.time", side_effect=self.test_fixed_time_taken),
            patch("log_structure.datetime") as mock_datetime,
        ):
            mock_datetime.now.return_value = self.fixed_datetime
            send_request_to_lambda(self.message_body_with_diagnostics)

        self.assertEqual(str(context.exception), "Unable to obtain IMMS ID")

        self.assertGreater(len(log.output), 0)
        log_json = self.extract_log_json(log)
        expected_log_json = deepcopy(self.expected_log_json_failure)
        expected_log_json["action_flag"] = "UPDATE"
        self.assertEqual(log_json, expected_log_json)

        mock_firehose_logger.forwarder_send_log.assert_called_once_with({"event": log_json})
        mock_firehose_logger.forwarder_send_log.reset_mock()

    def test_splunk_logging_failure_during_forwarding(self):
        """
        Test that for a row which failed processing (and therefore has diagnostics in the message recevied from
        kinesis), the log_json has all the expected keys and values, and the firehose logger is called with the
        log_json.
        """
        for operation in ["create"]:
            with self.subTest(operation):
                with (
                    self.assertLogs(level="INFO") as log,
                    self.assertRaises(MessageNotSuccessfulError) as context,
                    patch("log_structure.firehose_logger") as mock_firehose_logger,
                    patch("time.time", side_effect=self.test_fixed_time_taken),
                    patch("log_structure.datetime") as mock_datetime,
                    patch(
                        f"send_request_to_lambda.send_{operation}_request",
                        side_effect=MessageNotSuccessfulError(f"API Error: Unable to {operation} resource"),
                    ),
                ):
                    mock_datetime.now.return_value = self.fixed_datetime
                    message_body = deepcopy(self.message_body_success)
                    message_body["operation_requested"] = operation.upper()
                    send_request_to_lambda(message_body)

                self.assertEqual(str(context.exception), f"API Error: Unable to {operation} resource")

                self.assertGreater(len(log.output), 0)
                log_json = self.extract_log_json(log)
                expected_log_json = deepcopy(self.expected_log_json_failure)
                expected_log_json["action_flag"] = operation.upper()
                expected_log_json["error"] = f"API Error: Unable to {operation} resource"
                self.assertEqual(log_json, expected_log_json)

                mock_firehose_logger.forwarder_send_log.assert_called_once_with({"event": log_json})
                mock_firehose_logger.forwarder_send_log.reset_mock()
