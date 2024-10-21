import unittest
from mappings import map_target_disease
from tests.utils_for_recordprocessor_tests.values_for_recordprocessor_tests import TARGET_DISEASE_ELEMENTS


class TestMapTargetDisease(unittest.TestCase):
    """
    Test that map_target_disease returns the correct target disease element for valid vaccine types, or [] for
    invalid vaccine types.
    """

    def test_map_target_disease_valid(self):
        """Tests map_target_disease returns the disease coding information when using valid vaccine types"""
        # TODO: Confirm which vaccine types should be tested for
        # NOTE: TEST CASES SHOULD INCLUDE ALL VACCINE TYPES WHICH ARE VALID FOR THIS PRODUCT.
        # A NEW VACCINE TYPE SHOULD BE ADDED EVERY TIME THERE IS A VACCINE TYPE UPLIFT
        # (note that this will require adding the vaccine type to the TARGET_DISEASE_ELEMENTS)
        vaccine_types = ["RSV"]
        for vaccine_type in vaccine_types:
            with self.subTest(vaccine=vaccine_type):
                self.assertEqual(map_target_disease(vaccine_type), TARGET_DISEASE_ELEMENTS[vaccine_type])

    def test_map_target_disease_invalid(self):
        """Tests map_target_disease does not return the disease coding information when using invalid vaccine types."""
        for vaccine in ["non_existent_vaccine", "invalid_vaccine"]:
            with self.subTest(vaccine=vaccine):
                actual_result = map_target_disease(vaccine)
                self.assertEqual(actual_result, [])


if __name__ == "__main__":
    unittest.main()
