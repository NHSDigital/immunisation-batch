import unittest
from unittest.mock import patch, MagicMock
from io import StringIO
import json
import csv
import boto3
from moto import mock_s3, mock_kinesis
from batch_processing import (
    main,
    process_csv_to_fhir,
    get_environment,
)
from convert_fhir_json import convert_to_fhir_json
from utils_for_recordprocessor import get_csv_content_dict_reader
from get_action_flag_permissions import get_supplier_permissions, get_action_flag_permissions
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    SOURCE_BUCKET_NAME,
    DESTINATION_BUCKET_NAME,
    AWS_REGION,
    STREAM_NAME,
    MOCK_ENVIRONMENT_DICT,
    TEST_FILE_KEY,
    TEST_ACK_FILE_KEY,
    TEST_EVENT,
    VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE,
    TEST_PERMISSIONS_CONFIG,
    TestValues,
)

s3_client = boto3.client("s3", region_name=AWS_REGION)
kinesis_client = boto3.client("kinesis", region_name=AWS_REGION)


@patch.dict("os.environ", MOCK_ENVIRONMENT_DICT)
@mock_s3
@mock_kinesis
class TestProcessLambdaFunction(unittest.TestCase):

    def setUp(self) -> None:
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})

        self.results = {
            "resourceType": "Bundle",
            "type": "searchset",
            "link": [
                {
                    "relation": "self",
                    "url": (
                        "https://internal-dev.api.service.nhs.uk/immunisation-fhir-api-pr-224/"
                        "Immunization?immunization.identifier=https://supplierABC/identifiers/"
                        "vacc|b69b114f-95d0-459d-90f0-5396306b3794&_elements=id,meta"
                    ),
                }
            ],
            "entry": [
                {
                    "fullUrl": "https://api.service.nhs.uk/immunisation-fhir-api/"
                    "Immunization/277befd9-574e-47fe-a6ee-189858af3bb0",
                    "resource": {
                        "resourceType": "Immunization",
                        "id": "277befd9-574e-47fe-a6ee-189858af3bb0",
                        "meta": {"versionId": 1},
                    },
                }
            ],
            "total": 1,
        }, 200

    def tearDown(self) -> None:
        for bucket_name in [SOURCE_BUCKET_NAME, DESTINATION_BUCKET_NAME]:
            for obj in s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", []):
                s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])
            s3_client.delete_bucket(Bucket=bucket_name)

    @staticmethod
    def upload_source_file(file_key, file_content):
        """
        Uploads a test file with the TEST_FILE_KEY (Flu EMIS file) the given file content to the source bucket
        """
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=file_key, Body=file_content)

    @staticmethod
    def setup_kinesis(stream_name=STREAM_NAME):
        """Sets up the kinesis stream. Obtains a shard iterator. Returns the kinesis client and shard iterator"""
        kinesis_client.create_stream(StreamName=stream_name, ShardCount=1)

        # Obtain the first shard
        response = kinesis_client.describe_stream(StreamName=stream_name)
        shards = response["StreamDescription"]["Shards"]
        shard_id = shards[0]["ShardId"]

        # Get a shard iterator (using iterator type "TRIM_HORIZON" to read from the beginning)
        shard_iterator = kinesis_client.get_shard_iterator(
            StreamName=stream_name, ShardId=shard_id, ShardIteratorType="TRIM_HORIZON"
        )["ShardIterator"]

        return shard_iterator

    def assert_value_in_ack_file(self, value):
        """Downloads the ack file, decodes its content and returns the content"""
        response = s3_client.get_object(Bucket=DESTINATION_BUCKET_NAME, Key=TEST_ACK_FILE_KEY)
        content = response["Body"].read().decode("utf-8")
        self.assertIn(value, content)

    @patch("batch_processing.process_csv_to_fhir")
    @patch("batch_processing.get_action_flag_permissions")
    def test_lambda_handler(self, mock_get_action_flag_permissions, mock_process_csv_to_fhir):
        mock_get_action_flag_permissions.return_value = {"NEW", "UPDATE", "DELETE"}
        message_body = {"vaccine_type": "COVID19", "supplier": "Pfizer", "filename": "testfile.csv"}

        main(json.dumps(message_body))

        mock_process_csv_to_fhir.assert_called_once_with(incoming_message_body=message_body)

    def test_fetch_file_from_s3(self):
        self.upload_source_file(TEST_FILE_KEY, VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)
        expected_output = csv.DictReader(StringIO(VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE), delimiter="|")
        result = get_csv_content_dict_reader(SOURCE_BUCKET_NAME, TEST_FILE_KEY)
        self.assertEqual(list(result), list(expected_output))

    @patch("batch_processing.send_to_kinesis")
    def test_process_csv_to_fhir(self, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=self.results), patch(
            "batch_processing.get_action_flag_permissions", return_value={"NEW", "UPDATE", "DELETE"}
        ):
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    @patch("utils_for_recordprocessor.DictReader")
    def test_process_csv_to_fhir_positive_string_provided(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=self.results), patch(
            "batch_processing.get_action_flag_permissions", return_value={"NEW", "UPDATE", "DELETE"}
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_request_dose_sequence_string)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    @patch("utils_for_recordprocessor.DictReader")
    def test_process_csv_to_fhir_only_mandatory(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=self.results), patch(
            "batch_processing.get_action_flag_permissions", return_value={"NEW", "UPDATE", "DELETE"}
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_request_only_mandatory)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    @patch("utils_for_recordprocessor.DictReader")
    def test_process_csv_to_fhir_positive_string_not_provided(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=self.results), patch(
            "batch_processing.get_action_flag_permissions", return_value={"NEW", "UPDATE", "DELETE"}
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_request_dose_sequence_missing)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    @patch("utils_for_recordprocessor.DictReader")
    def test_process_csv_to_fhir_invalid(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body=VALID_FILE_CONTENT_WITH_NEW_AND_UPDATE)

        with patch("process_row.convert_to_fhir_json", return_value=({}, False)), patch(
            "batch_processing.get_action_flag_permissions", return_value={"NEW", "UPDATE", "DELETE"}
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_request_only_mandatory)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("fatal-error")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    @patch("utils_for_recordprocessor.DictReader")
    def test_process_csv_to_fhir_paramter_missing(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body="")

        with patch("process_row.convert_to_fhir_json", return_value=({}, True)), patch(
            "batch_processing.get_action_flag_permissions", return_value={"NEW", "UPDATE", "DELETE"}
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_request_params_missing)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("fatal-error")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    @patch("utils_for_recordprocessor.DictReader")
    def test_process_csv_to_fhir_failed(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body="")

        with patch("process_row.convert_to_fhir_json", return_value=({}, True)), patch(
            "process_row.ImmunizationApi.get_imms_id", return_value=({"total": 0}, 400)
        ), patch("batch_processing.get_action_flag_permissions", return_value={"NEW", "UPDATE", "DELETE"}):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_update_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("fatal-error")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    @patch("utils_for_recordprocessor.DictReader")
    def test_process_csv_to_fhir_successful(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body="")

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=self.results), patch(
            "batch_processing.get_action_flag_permissions", return_value={"NEW", "UPDATE", "DELETE"}
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_update_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("Success")
        mock_send_to_kinesis.assert_called()

    @patch("batch_processing.send_to_kinesis")
    @patch("utils_for_recordprocessor.DictReader")
    def test_process_csv_to_fhir_incorrect_permissions(self, mock_csv_dict_reader, mock_send_to_kinesis):
        s3_client.put_object(Bucket=SOURCE_BUCKET_NAME, Key=TEST_FILE_KEY, Body="")

        with patch("process_row.ImmunizationApi.get_imms_id", return_value=self.results), patch(
            "batch_processing.get_action_flag_permissions", return_value={"DELETE"}
        ):
            mock_csv_reader_instance = MagicMock()
            mock_csv_reader_instance.__iter__.return_value = iter(TestValues.mock_update_request)
            mock_csv_dict_reader.return_value = mock_csv_reader_instance
            process_csv_to_fhir(TEST_EVENT)

        self.assert_value_in_ack_file("No permissions for operation")
        mock_send_to_kinesis.assert_called()

    def test_process_csv_to_fhir_successful_Practitioner(self):
        request = TestValues.update_request
        request["PERFORMING_PROFESSIONAL_FORENAME"] = ""
        request["PERFORMING_PROFESSIONAL_SURNAME"] = ""
        vaccine_type = "flu"

        json_result, _ = convert_to_fhir_json(request, vaccine_type)

        self.assertNotIn("Practitioner", [res["resourceType"] for res in json_result.get("contained", [])])
        self.assertNotIn(
            "reference",
            [
                performer.get("reference")
                for res in json_result.get("actor", [])
                if "performer" in res
                for performer in res.get("performer", [])
            ],
        )

    def test_process_csv_to_fhir_successful_qualitycode(self):
        request = TestValues.update_request
        request["DOSE_UNIT_CODE"] = ""
        vaccine_type = "flu"

        json_result, _ = convert_to_fhir_json(request, vaccine_type)
        dose_quality = json_result.get("doseQuality", {})
        self.assertNotIn("system", dose_quality)

    def test_process_csv_to_fhir_successful_vaccine_code(self):
        request = TestValues.update_request
        request["VACCINE_PRODUCT_CODE"] = ""
        request["VACCINE_PRODUCT_TERM"] = ""
        vaccine_type = "flu"

        json_result, _ = convert_to_fhir_json(request, vaccine_type)
        vaccine_code = json_result.get("vaccineCode", {})
        self.assertIn("NAVU", vaccine_code["coding"][0]["code"])
        self.assertIn("Not available", vaccine_code["coding"][0]["display"])

    def test_get_environment(self):
        with patch("batch_processing.os.getenv", return_value="internal-dev"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

        with patch("batch_processing.os.getenv", return_value="prod"):
            env = get_environment()
            self.assertEqual(env, "prod")

        with patch("batch_processing.os.getenv", return_value="unknown-env"):
            env = get_environment()
            self.assertEqual(env, "internal-dev")

    @patch("get_action_flag_permissions.get_permissions_config_json_from_s3")
    def test_get_supplier_permissions_success(self, mock_get_permissions_config_json_from_s3):
        mock_get_permissions_config_json_from_s3.return_value = TEST_PERMISSIONS_CONFIG

        supplier = "SUPPLIER1"

        permissions = get_supplier_permissions(supplier)

        self.assertEqual(permissions, ["COVID19_CREATE", "COVID19_DELETE", "COVID19_UPDATE"])

    @patch("get_action_flag_permissions.get_permissions_config_json_from_s3")
    def test_get_supplier_permissions_no_permissions(self, mock_get_permissions_config_json_from_s3):
        mock_get_permissions_config_json_from_s3.return_value = TEST_PERMISSIONS_CONFIG

        supplier = "SUPPLIER4"

        permissions = get_supplier_permissions(supplier)

        self.assertEqual(permissions, [""])

    def test_no_permissions(self):
        with patch("get_action_flag_permissions.get_supplier_permissions", return_value=[]):
            self.assertEqual(get_action_flag_permissions("test_supplier", "FLU"), set())

    def test_full_permissions(self):
        with patch("get_action_flag_permissions.get_supplier_permissions", return_value=["FLU_FULL", "MMR_CREATE"]):
            self.assertEqual(get_action_flag_permissions("test_supplier", "FLU"), {"NEW", "UPDATE", "DELETE"})

    def test_partial_permissions(self):
        with patch(
            "get_action_flag_permissions.get_supplier_permissions",
            return_value=["FLU_CREATE", "FLU_DELETE", "MMR_CREATE"],
        ):
            self.assertEqual(get_action_flag_permissions("test_supplier", "FLU"), {"NEW", "DELETE"})

    @patch("get_action_flag_permissions.get_supplier_permissions")
    def test_get_action_flag_permissions_success(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["MMR_FULL", "FLU_CREATE", "FLU_UPDATE"]

        supplier = "supplier1"
        vaccine_type = "FLU"

        operations = get_action_flag_permissions(supplier, vaccine_type)

        self.assertEqual(operations, {"UPDATE", "NEW"})

    @patch("get_action_flag_permissions.get_supplier_permissions")
    def test_get_action_flag_permissions_one_permission(self, mock_get_supplier_permissions):
        mock_get_supplier_permissions.return_value = ["MMR_UPDATE"]

        supplier = "supplier1"
        vaccine_type = "MMR"

        operations = get_action_flag_permissions(supplier, vaccine_type)

        self.assertEqual(operations, {"UPDATE"})


if __name__ == "__main__":
    unittest.main()
