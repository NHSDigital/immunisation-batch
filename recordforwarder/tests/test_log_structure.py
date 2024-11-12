# import unittest
# from unittest.mock import patch
# import json
# from datetime import datetime
# from send_request_to_lambda import send_request_to_lambda
# from tests.utils_for_recordfowarder_tests.values_for_recordforwarder_tests import (
#     TEST_IMMS_ID,
#     test_fixed_time_taken,
# )
# from errors import MessageNotSuccessfulError


# class Test_Splunk_logging(unittest.TestCase):
#     def setUp(self):
#         self.message_body_base = {
#             "row_id": "6543219",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "supplier": "EMIS",
#             "operation_requested": "operation_requested",
#             "fhir_json": {"resourceType": "Immunization"},
#         }

#         self.fixed_datetime = datetime(2024, 10, 29, 12, 0, 0)

#         self.message_body_base_errors = {
#             "row_id": "6543219",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "supplier": "EMIS",
#             "operation_requested": "UPDATE",
#             "diagnostics": "Unable to obtain IMMS ID",
#         }

#         self.expected_values = {
#             "function_name": "send_request_to_lambda",
#             "date_time": self.fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
#             "status": "success",
#             "supplier": "EMIS",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "vaccine_type": "FLU",
#             "message_id": "6543219",
#             "action_flag": "action_flag",
#             "time_taken": 1.0,
#         }

#         # Expected splunk log values when there is an error
#         self.expected_values_error = {
#             "event": {
#                 "function_name": "send_request_to_lambda",
#                 "date_time": self.fixed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
#                 "status": "Fail",
#                 "supplier": "EMIS",
#                 "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#                 "vaccine_type": "FLU",
#                 "message_id": "6543219",
#                 "action_flag": "UPDATE",
#                 "time_taken": "1.0s",
#                 "status_code": 400,
#                 "error": "Unable to obtain IMMS ID",
#             }
#         }

#     def extract_log_json(self, log_entry):
#         """Extracts JSON from log entry."""
#         json_start = log_entry.find("{")
#         json_str = log_entry[json_start:]
#         return json.loads(json_str)

#     @patch("send_request_to_lambda.send_create_request")
#     @patch("send_request_to_lambda.send_update_request")
#     @patch("send_request_to_lambda.send_delete_request")
#     @patch("log_structure.firehose_logger")
#     @patch("time.time")
#     @patch("log_structure.datetime")
#     def test_splunk_logging_successful_rows(
#         self,
#         mock_datetime,
#         mock_time,
#         mock_firehose_logger,
#         mock_send_delete_request,
#         mock_send_update_request,
#         mock_send_create_request,
#     ):

#         # mocking datetime and time_taken as fixed values
#         mock_datetime.now.return_value = self.fixed_datetime
#         mock_time.side_effect = test_fixed_time_taken

#         # Mock return values for each operation
#         mock_send_create_request.return_value = TEST_IMMS_ID
#         mock_send_update_request.return_value = TEST_IMMS_ID
#         mock_send_delete_request.return_value = TEST_IMMS_ID
#         operations = [
#             {"operation_requested": "CREATE"},
#             {"operation_requested": "UPDATE"},
#             {"operation_requested": "DELETE"},
#         ]

#         for op in operations:
#             with self.assertLogs(level="INFO") as log:
#                 message_body = self.message_body_base.copy()
#                 message_body["operation_requested"] = op["operation_requested"]

#                 result = send_request_to_lambda(message_body)
#                 self.assertEqual(result, "imms_6543219")
#                 self.assertGreater(len(log.output), 0)

#                 log_json = self.extract_log_json(log.output[0])

#                 expected_values = self.expected_values
#                 expected_values["action_flag"] = op["operation_requested"]

#                 # Iterate over the expected values and assert each one
#                 for key, expected in expected_values.items():
#                     self.assertEqual(log_json[key], expected)

#                 self.assertIsInstance(log_json["time_taken"], float)

#                 # Check firehose logging call
#                 mock_firehose_logger.forwarder_send_log.assert_called_once_with({"event": log_json})
#                 mock_firehose_logger.forwarder_send_log.reset_mock()

#     @patch("log_structure.firehose_logger")
#     @patch("log_structure.logger")
#     @patch("time.time")
#     @patch("log_structure.datetime")
#     def test_splunk_logging_diagnostics_error(self, mock_datetime, mock_time, mock_logger, mock_firehose_logger):
#         # Message body with diagnostics to trigger an error, mocking datetime and time_taken as fixed values
#         mock_datetime.now.return_value = self.fixed_datetime
#         mock_time.side_effect = test_fixed_time_taken
#         message_body = self.message_body_base_errors

#         # Exception raised in send_request_to_lambda
#         with self.assertRaises(MessageNotSuccessfulError) as context:
#             send_request_to_lambda(message_body)

#         # Ensure the exception message is as expected
#         self.assertEqual(str(context.exception), "Unable to obtain IMMS ID")

#         log_data = mock_logger.exception.call_args[0][0]

#         self.assertIn("Unable to obtain IMMS ID", log_data)

#         firehose_log_data = self.expected_values_error
#         mock_firehose_logger.forwarder_send_log.assert_called_once_with(firehose_log_data)

#     @patch("send_request_to_lambda.send_create_request")
#     @patch("send_request_to_lambda.send_update_request")
#     @patch("send_request_to_lambda.send_delete_request")
#     @patch("send_request_to_lambda.forwarder_function_info")  # Mock the decorator to simplify the test
#     @patch("log_structure.logger")  # Patch the logger to verify error logs
#     def test_error_logging_in_send_request_to_lambda(
#         self,
#         mock_logger,
#         mock_forwarder_function_info,
#         mock_send_delete_request,
#         mock_send_update_request,
#         mock_send_create_request,
#     ):

#         # Define message bodies for each operation to trigger errors
#         create_message_body = {
#             "operation_requested": "CREATE",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "supplier": "TestSupplier",
#             "fhir_json": {},  # Placeholder for any necessary data structure
#             "row_id": "12345",
#         }

#         update_message_body = {
#             "operation_requested": "UPDATE",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "supplier": "TestSupplier",
#             "fhir_json": {},  # Placeholder for any necessary data structure
#             "row_id": "12345",
#             "imms_id": "67890",
#             "version": "1",
#         }

#         delete_message_body = {
#             "operation_requested": "DELETE",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "supplier": "TestSupplier",
#             "fhir_json": {},  # Placeholder for any necessary data structure
#             "imms_id": "67890",
#         }

#         # Set up each mock function to raise MessageNotSuccessfulError with custom error messages
#         mock_send_create_request.side_effect = MessageNotSuccessfulError("API Error: Unable to create resource")
#         mock_send_update_request.side_effect = MessageNotSuccessfulError("API Error: Unable to update resource")
#         mock_send_delete_request.side_effect = MessageNotSuccessfulError("API Error: Unable to delete resource")

#         # Test the CREATE operation
#         with self.assertRaises(MessageNotSuccessfulError):
#             send_request_to_lambda(create_message_body)

#         # Assert the logger recorded the error message for CREATE
#         mock_logger.exception.assert_called()  # Check that the log was triggered
#         self.assertIn("API Error: Unable to create resource", str(mock_logger.exception.call_args))  # Verify message

#         # Reset the mock logger for the next test case
#         mock_logger.exception.reset_mock()

#         # Test the UPDATE operation
#         with self.assertRaises(MessageNotSuccessfulError):
#             send_request_to_lambda(update_message_body)

#         # Assert the logger recorded the error message for UPDATE
#         mock_logger.exception.assert_called()
#         self.assertIn("API Error: Unable to update resource", str(mock_logger.exception.call_args))

#         # Reset the mock logger for the next test case
#         mock_logger.exception.reset_mock()

#         # Test the DELETE operation
#         with self.assertRaises(MessageNotSuccessfulError):
#             send_request_to_lambda(delete_message_body)

#         # Assert the logger recorded the error message for DELETE
#         mock_logger.exception.assert_called()
#         self.assertIn("API Error: Unable to delete resource", str(mock_logger.exception.call_args))

#     @patch("send_request_to_lambda.send_create_request")
#     @patch("send_request_to_lambda.send_update_request")
#     @patch("send_request_to_lambda.send_delete_request")
#     @patch("log_structure.logger")  # Patch the logger to verify error logs
#     def test_error_logging_operation(
#         self,
#         mock_logger,
#         mock_send_delete_request,
#         mock_send_update_request,
#         mock_send_create_request,
#     ):

#         create_message_body = {
#             "row_id": "555555",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "supplier": "EMIS",
#             "operation_requested": "CREATE",
#             "fhir_json": {"resourceType": "Immunization"},
#         }

#         update_message_body = {
#             "row_id": "7891011",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "supplier": "EMIS",
#             "operation_requested": "UPDATE",
#             "fhir_json": {"resourceType": "Immunization"},
#         }

#         delete_message_body = {
#             "row_id": "12131415",
#             "file_key": "flu_Vaccinations_v5_8HK48_20210730T12000000.csv",
#             "supplier": "EMIS",
#             "operation_requested": "DELETE",
#             "fhir_json": {"resourceType": "Immunization"},
#         }

#         # Set up each mock function to raise MessageNotSuccessfulError with custom error messages
#         mock_send_create_request.side_effect = MessageNotSuccessfulError("API Error: Unable to create resource")
#         mock_send_update_request.side_effect = MessageNotSuccessfulError("API Error: Unable to update resource")
#         mock_send_delete_request.side_effect = MessageNotSuccessfulError("API Error: Unable to delete resource")

#         with self.assertRaises(MessageNotSuccessfulError):
#             send_request_to_lambda(create_message_body)

#         mock_logger.exception.assert_called()
#         self.assertIn("API Error: Unable to create resource", str(mock_logger.exception.call_args))
#         mock_logger.exception.reset_mock()

#         # Test the UPDATE operation
#         with self.assertRaises(MessageNotSuccessfulError):
#             send_request_to_lambda(update_message_body)

#         mock_logger.exception.assert_called()
#         self.assertIn("API Error: Unable to update resource", str(mock_logger.exception.call_args))
#         mock_logger.exception.reset_mock()

#         # Test the DELETE operation
#         with self.assertRaises(MessageNotSuccessfulError):
#             send_request_to_lambda(delete_message_body)

#         mock_logger.exception.assert_called()
#         self.assertIn("API Error: Unable to delete resource", str(mock_logger.exception.call_args))


# if __name__ == "__main__":
#     unittest.main()
