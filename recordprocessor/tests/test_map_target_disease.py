import unittest
from mappings import map_target_disease
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import (
    mock_disease_codes,
    mock_disease_display_terms,
    MOCK_VACCINE_DISEASE_MAPPING,
)


def generate_map_target_disease():
    """Generate test cases for map_target_disease dynamically based on mock vaccine type data."""
    create_disease_coding = []

    for vaccine, diseases in MOCK_VACCINE_DISEASE_MAPPING.items():
        expected = []

        for disease in diseases:
            expected.append(
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": mock_disease_codes[disease],
                            "display": mock_disease_display_terms[disease],
                        }
                    ]
                }
            )

        create_disease_coding.append({"vaccine": vaccine, "expected": expected})
    return create_disease_coding


class TestMapTargetDisease(unittest.TestCase):

    def test_map_target_disease_valid(self):
        """Tests map_target_disease returns the disease coding information when using valid vaccine types"""
        disease_coding = generate_map_target_disease()

        for case in disease_coding:
            with self.subTest(vaccine=case["vaccine"]):
                self.assertEqual(map_target_disease(case["vaccine"]), case["expected"])

    def test_map_target_disease_invalid(self):
        """Tests map_target_disease does not return the disease coding information when using invalid vaccine types."""
        invalid_test_cases = [
            {
                "vaccine": "non_existent_vaccine",
                "expected_output": [
                    {
                        "coding": [
                            {"system": "http://snomed.info/sct", "code": "invalid_code", "display": "invalid_display"}
                        ]
                    }
                ],
            },
            {
                "vaccine": "invalid_vaccine",
                "expected_output": [
                    {
                        "coding": [
                            {"system": "http://snomed.info/sct", "code": "unknown_code", "display": "unknown_display"}
                        ]
                    }
                ],
            },
        ]  # Invalid vaccine and output

        for case in invalid_test_cases:
            with self.subTest(vaccine=case["vaccine"]):
                actual_result = map_target_disease(case["vaccine"])
                self.assertNotEqual(actual_result, case["expected_output"])
                self.assertEqual(actual_result, [])
