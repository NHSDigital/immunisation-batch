# """Tests for convert_to_fhir_imms_resource"""

# import unittest
# import os
# import sys
# maindir = os.path.dirname(__file__)
# srcdir = '../src'
# sys.path.insert(0, os.path.abspath(os.path.join(maindir, srcdir)))
# from convert_to_fhir_imms_resource import convert_to_fhir_imms_resource  # noqa: E402

# # Do not try from src.mappings import Vaccine as this imports a different instance of Vaccine and tests will break
# from mappings import Vaccine  # noqa: E402
# from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (  # noqa: E402
#     all_fields,
#     mandatory_fields_only,
#     all_fields_fhir_imms_resource,
#     mandatory_fields_only_fhir_imms_resource,
#     critical_fields_only,
#     critical_fields_only_fhir_imms_resource,
# )


# class TestConvertToFhirImmsResource(unittest.TestCase):
#     """Tests for convert_to_fhir_imms_resource"""

#     def test_convert_to_fhir_imms_resource(self):
#         """
#         Test that convert_to_fhir_imms_resource gives the expected output. These tests check that the entire
#         outputted FHIR Immunization Resource matches the expected output.
#         """
#         # Test cases tuples are structure as (test_name, input_values, expected_output)
#         cases = [
#             ("All fields", all_fields, all_fields_fhir_imms_resource),
#             ("Mandatory fields only", mandatory_fields_only, mandatory_fields_only_fhir_imms_resource),
#             ("Critical fields only", critical_fields_only, critical_fields_only_fhir_imms_resource),
#         ]

#         for test_name, input_values, expected_output in cases:
#             with self.subTest(test_name):
#                 self.assertEqual(convert_to_fhir_imms_resource(input_values, Vaccine.RSV), expected_output)
