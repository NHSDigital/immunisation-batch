import unittest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime
import time
from send_request_to_lambda import send_request_to_lambda
from errors import MessageNotSuccessfulError
from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import TEST_IMMS_ID


class TestSendRequestToLambda(unittest.TestCase):
    def setUp(self):
        self.message_body_base = {
            "row_id": "6543219",
            "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
            "supplier": "EMIS",
            "operation_requested": "operation_requested",
            "fhir_json": {"resourceType": "Immunization"},
        }

    def extract_log_json(self, log_entry):
        """Extracts JSON from log entry."""
        json_start = log_entry.find("{")
        json_str = log_entry[json_start:]
        return json.loads(json_str)

    @patch("send_request_to_lambda.send_create_request")
    @patch("log_structure.firehose_logger")
    @patch("time.time")
    @patch("log_structure.datetime")
    def test_splunk_logging_create(self, mock_datetime, mock_time, mock_firehose_logger, mock_send_create_request):
        fixed_time = datetime(2024, 10, 29, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        mock_time.side_effect = [1000000.0, 1000001.0, 1000001.0]
        mock_send_create_request.return_value = TEST_IMMS_ID
        with self.assertLogs(level="INFO") as log:
            message_body = self.message_body_base.copy()
            message_body["operation_requested"] = "CREATE"

            result = send_request_to_lambda(message_body)
            print(f"{result}")
            self.assertEqual(result, "imms_6543219")
            self.assertGreater(len(log.output), 0)

            log_json = self.extract_log_json(log.output[0])

            expected_values = {
                "function_name": "send_request_to_lambda",
                "date_time": fixed_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success",
                "supplier": "EMIS",
                "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
                "vaccine_type": "FLU",
                "message_id": "6543219",
                "action_flag": "CREATE",
                "time_taken": 1.0,
            }

            self.assertEqual(log_json, expected_values)

            self.assertIsInstance(log_json["time_taken"], float)

            # Check firehose logging call
            mock_firehose_logger.forwarder_send_log.assert_called_once_with({"event": log_json})
            mock_firehose_logger.forwarder_send_log.reset_mock()

    @patch("send_request_to_lambda.send_update_request")
    @patch("log_structure.firehose_logger")
    @patch("time.time")
    @patch("log_structure.datetime")
    @patch("send_request_to_lambda.MessageNotSuccessfulError")
    def test_splunk_logging_update(
        self, mock_MessageNotSuccessfulError, mock_datetime, mock_time, mock_firehose_logger, mock_send_update_request
    ):
        fixed_time = datetime(2024, 10, 29, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        mock_time.side_effect = [1000000.0, 1000001.0, 1000001.0]
        mock_send_update_request.return_value = TEST_IMMS_ID
        mock_MessageNotSuccessfulError.return_value = "Unable to obtain imms event id"
        with self.assertLogs(level="INFO") as log:
            message_body = self.message_body_base.copy()
            message_body["operation_requested"] = "UPDATE"

            result = send_request_to_lambda(message_body)
            print(f"{result}")
            self.assertEqual(result, "imms_6543219")
            self.assertGreater(len(log.output), 0)

            log_json = self.extract_log_json(log.output[0])

            expected_values = {
                "function_name": "send_request_to_lambda",
                "date_time": fixed_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success",
                "supplier": "EMIS",
                "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
                "vaccine_type": "FLU",
                "message_id": "6543219",
                "action_flag": "UPDATE",
                "time_taken": 1.0,
            }

            self.assertEqual(log_json, expected_values)

            self.assertIsInstance(log_json["time_taken"], float)

            # Check firehose logging call
            mock_firehose_logger.forwarder_send_log.assert_called_once_with({"event": log_json})
            mock_firehose_logger.forwarder_send_log.reset_mock()

    @patch("send_request_to_lambda.send_delete_request")
    @patch("log_structure.firehose_logger")
    @patch("time.time")
    @patch("log_structure.datetime")
    def test_splunk_logging_delete(self, mock_datetime, mock_time, mock_firehose_logger, mock_send_delete_request):
        fixed_time = datetime(2024, 10, 29, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        mock_time.side_effect = [1000000.0, 1000001.0, 1000001.0]
        mock_send_delete_request.return_value = TEST_IMMS_ID
        with self.assertLogs(level="INFO") as log:
            message_body = self.message_body_base.copy()
            message_body["operation_requested"] = "DELETE"

            result = send_request_to_lambda(message_body)
            print(f"{result}")
            self.assertEqual(result, "imms_6543219")
            self.assertGreater(len(log.output), 0)

            log_json = self.extract_log_json(log.output[0])

            expected_values = {
                "function_name": "send_request_to_lambda",
                "date_time": fixed_time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "success",
                "supplier": "EMIS",
                "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
                "vaccine_type": "FLU",
                "message_id": "6543219",
                "action_flag": "DELETE",
                "time_taken": 1.0,
            }

            self.assertEqual(log_json, expected_values)

            self.assertIsInstance(log_json["time_taken"], float)

            # Check firehose logging call
            mock_firehose_logger.forwarder_send_log.assert_called_once_with({"event": log_json})
            mock_firehose_logger.forwarder_send_log.reset_mock()


if __name__ == "__main__":
    unittest.main()
