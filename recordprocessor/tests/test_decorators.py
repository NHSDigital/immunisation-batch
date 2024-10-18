"""
Test each decorator in the transformer module.
Each decorator has its own test class, which tests various potential combinations of headers.
NOTE: testing protected methods is not ideal. But in this case, we are testing the decorators in isolation.
NOTE: the public function `decorate` is tested in `TestDecorate` class.
"""

from decimal import Decimal
import copy
import unittest

from src.convert_to_fhir_imms_resource import (
    _decorate_patient,
    _decorate_vaccination,
    _decorate_vaccine,
    _decorate_performer,
    _decorate_immunization,
    _decorate_protocol_applied,
)
from src.mappings import map_target_disease
from tests.utils_for_recordprocessor_tests.decorator_constants import (
    AllHeaders,
    AllHeadersExpectedOutput,
    ExtensionItems,
    COVID_19_TARGET_DISEASE_ELEMENT,
)

raw_imms: dict = {"resourceType": "Immunization", "contained": [], "status": "completed"}


class TestImmunizationDecorator(unittest.TestCase):
    """Tests for _decorate_immunization"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_headers(self):
        """
        Test that all immunization fields are added when all the relevant immunization fields contain non-empty data
        """
        _decorate_immunization(self.imms, AllHeaders.immunization)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.immunization)

    def test_no_immunization_headers(self):
        """Test that no fields are added when no immunization fields contain non-empty data"""
        _decorate_immunization(self.imms, {"UNIQUE_ID": ""})
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": [], "status": "completed"})

    def test_unique_id(self):
        """Test that only non-empty unique_id values are added"""
        # unique_id non-empty, unique_uri empty
        _decorate_immunization(self.imms, {"UNIQUE_ID": "a_unique_id", "UNIQUE_ID_URI": None})
        self.assertListEqual(self.imms["identifier"], [{"value": "a_unique_id"}])

        # Unique_id empty, unique_uri non-empty
        _decorate_immunization(self.imms, {"UNIQUE_ID_URI": "a_unique_id_uri"})
        self.assertListEqual(self.imms["identifier"], [{"system": "a_unique_id_uri"}])


class TestPatientDecorator(unittest.TestCase):
    """Tests for _decorate_patient"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_patient_headers(self):
        """Test that all patient fields are added when all patient fields contain non-empty data"""
        _decorate_patient(self.imms, AllHeaders.patient)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.patient)

    def test_no_patient_headers(self):
        """Test that no fields are added when no patient fields contain non-empty data"""
        _decorate_patient(self.imms, {})
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": [], "status": "completed"})

    def test_one_patient_header(self):
        """Test that patient fields are added when one patient field contains non-empty data"""
        _decorate_patient(self.imms, {"PERSON_DOB": "19930821"})
        expected_imms = {
            "resourceType": "Immunization",
            "status": "completed",
            "contained": [{"resourceType": "Patient", "id": "Patient1", "birthDate": "1993-08-21"}],
            "patient": {"reference": "#Patient1"},
        }
        self.assertDictEqual(self.imms, expected_imms)

    def test_person_name(self):
        """Test that only non-empty name values are added"""
        # Surname non-empty, forename empty
        imms = copy.deepcopy(self.imms)
        _decorate_patient(imms, {"PERSON_SURNAME": "a_surname", "PERSON_FORENAME": ""})
        self.assertListEqual(imms["contained"][0]["name"], [{"family": "a_surname"}])

        # Surname empty, forename non-empty
        imms = copy.deepcopy(self.imms)
        _decorate_patient(imms, {"PERSON_FORENAME": "a_forename"})
        self.assertListEqual(imms["contained"][0]["name"], [{"given": ["a_forename"]}])


class TestVaccineDecorator(unittest.TestCase):
    """Tests for _decorate_vaccine"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_vaccine_headers(self):
        """Test that all vaccine fields are added when all vaccine fields contain non-empty data"""
        _decorate_vaccine(self.imms, AllHeaders.vaccine)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.vaccine)

    def test_no_vaccine_headers(self):
        """Test that no fields are added when no vaccine fields contain non-empty data"""
        _decorate_vaccine(self.imms, {})
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": [], "status": "completed"})

    def test_vaccine_product(self):
        """Test that only non-empty vaccine_product values are added"""
        # vaccine_product: _code non-empty, term empty
        headers = {"VACCINE_PRODUCT_CODE": "a_vacc_code", "VACCINE_PRODUCT_TERM": ""}
        _decorate_vaccine(self.imms, headers)
        expected = {"coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_code"}]}
        self.assertDictEqual(self.imms["vaccineCode"], expected)

        # vaccine_product: _code empty, term non-empty
        headers = {"VACCINE_PRODUCT_CODE": "", "VACCINE_PRODUCT_TERM": "a_vacc_term"}
        _decorate_vaccine(self.imms, headers)
        expected = {"coding": [{"system": "http://snomed.info/sct", "display": "a_vacc_term"}]}
        self.assertDictEqual(self.imms["vaccineCode"], expected)


class TestVaccinationDecorator(unittest.TestCase):
    """Tests for _decorate_vaccination"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_vaccination_headers(self):
        """Test that all vaccination fields are added when all vaccination fields contain non-empty data"""
        _decorate_vaccination(self.imms, AllHeaders.vaccination)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.vaccination)

    def test_no_vaccination_headers(self):
        """Test that no fields are added when no vaccination fields contain non-empty data"""
        _decorate_vaccination(self.imms, {})
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "status": "completed", "contained": []})

    def test_vaccination_procedure(self):
        """Test that only non-empty vaccination_procedure values are added"""
        # vaccination_procedure: _code empty, _term non-empty
        _decorate_vaccination(self.imms, {"VACCINATION_PROCEDURE_TERM": "a_vaccination_procedure_term"})
        expected_extension_item = copy.deepcopy(ExtensionItems.vaccination_procedure)
        expected_extension_item["valueCodeableConcept"]["coding"][0].pop("code")
        self.assertListEqual(self.imms["extension"], [expected_extension_item])

        # vaccination_procedure: _code empty, _term non-empty
        _decorate_vaccination(self.imms, {"VACCINATION_PROCEDURE_CODE": "a_vaccination_procedure_code"})
        expected_extension_item = copy.deepcopy(ExtensionItems.vaccination_procedure)
        expected_extension_item["valueCodeableConcept"]["coding"][0].pop("display")
        self.assertListEqual(self.imms["extension"], [expected_extension_item])

    def test_site_of_vaccination(self):
        """Test that only non-empty site_of_vaccination values are added"""
        # site_of_vaccination: _code non-empty, _display empty
        _decorate_vaccination(self.imms, {"SITE_OF_VACCINATION_CODE": "a_vacc_site_code"})
        expected = {"coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_site_code"}]}
        self.assertDictEqual(self.imms["site"], expected)

        # site_of_vaccination: _code empty, _display non-empty
        _decorate_vaccination(self.imms, {"SITE_OF_VACCINATION_TERM": "a_vacc_site_term"})
        expected = {"coding": [{"system": "http://snomed.info/sct", "display": "a_vacc_site_term"}]}
        self.assertDictEqual(self.imms["site"], expected)

    def test_route_of_vaccination(self):
        """Test that only non-empty route_of_vaccination values are added"""
        # route_of_vaccination: _code non-empty, _display empty
        _decorate_vaccination(self.imms, {"ROUTE_OF_VACCINATION_CODE": "a_vacc_route_code"})
        expected = {"coding": [{"system": "http://snomed.info/sct", "code": "a_vacc_route_code"}]}
        self.assertDictEqual(self.imms["route"], expected)

        # route_of_vaccination: _code empty, _display non-empty
        _decorate_vaccination(self.imms, {"ROUTE_OF_VACCINATION_TERM": "a_vacc_route_term"})
        expected = {"coding": [{"system": "http://snomed.info/sct", "display": "a_vacc_route_term"}]}
        self.assertDictEqual(self.imms["route"], expected)

    def test_dose_quantity(self):
        """Test that only non-empty dose_quantity values (dose_amount, dose_unit_term and dose_unit_code) are added"""
        dose_quantity = {"system": "http://unitsofmeasure.org", "value": Decimal("0.5"), "unit": "t", "code": "code"}
        # dose: _amount non-empty, _unit_term non-empty, _unit_code empty
        headers = {"DOSE_AMOUNT": "0.5", "DOSE_UNIT_TERM": "a_dose_unit_term", "DOSE_UNIT_CODE": ""}
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "value": Decimal("0.5"), "unit": "a_dose_unit_term"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount non-empty, _unit_term empty, _unit_code non-empty
        headers = {"DOSE_AMOUNT": "0.5", "DOSE_UNIT_CODE": "a_dose_unit_code"}
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "value": Decimal("0.5"), "code": "a_dose_unit_code"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount empty, _unit_term non-empty, _unit_code non-empty
        headers = {"DOSE_UNIT_TERM": "a_dose_unit_term", "DOSE_UNIT_CODE": "a_dose_unit_code"}
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "code": "a_dose_unit_code", "unit": "a_dose_unit_term"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount non-empty, _unit_term empty, _unit_code empty
        headers = {"DOSE_AMOUNT": "2", "DOSE_UNIT_CODE": ""}
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "value": 2}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount empty, _unit_term non-empty, _unit_code empty
        headers = {"DOSE_UNIT_TERM": "a_dose_unit_term", "DOSE_UNIT_CODE": ""}
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "unit": "a_dose_unit_term"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)

        # dose: _amount empty, _unit_term empty, _unit_code non-empty
        headers = {"DOSE_UNIT_CODE": "a_dose_unit_code"}
        _decorate_vaccination(self.imms, headers)
        dose_quantity = {"system": "http://unitsofmeasure.org", "code": "a_dose_unit_code"}
        self.assertDictEqual(self.imms["doseQuantity"], dose_quantity)


class TestPerformerDecorator(unittest.TestCase):
    """Tests for _decorate_vaccination"""

    def setUp(self):
        self.imms = copy.deepcopy(raw_imms)

    def test_all_performer_headers(self):
        """Test that all performer fields are added when all performer fields contain non-empty data"""
        _decorate_performer(self.imms, AllHeaders.performer)
        self.assertDictEqual(self.imms, AllHeadersExpectedOutput.performer)

    def test_no_performer_headers(self):
        """Test that no fields are added when no performer fields contain non-empty data"""
        _decorate_performer(self.imms, {})
        self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": [], "status": "completed"})

    def test_one_performer_header(self):
        """Test that the relevant fields are added when one performer field contains non-empty data"""
        _decorate_performer(self.imms, {"SITE_CODE": "a_site_code"})
        expected_output = {
            "resourceType": "Immunization",
            "status": "completed",
            "contained": [],
            "performer": [{"actor": {"type": "Organization", "identifier": {"value": "a_site_code"}}}],
        }
        self.assertDictEqual(self.imms, expected_output)

    def test_one_practitioner_header(self):
        """Test that the relevant fields are added when one practitioner field contains non-empty data"""
        _decorate_performer(self.imms, {"PERFORMING_PROFESSIONAL_FORENAME": "a_prof_forename"})
        expected_output = {
            "resourceType": "Immunization",
            "status": "completed",
            "contained": [
                {
                    "resourceType": "Practitioner",
                    "id": "Practitioner1",
                    "name": [{"given": ["a_prof_forename"]}],
                }
            ],
            "performer": [{"actor": {"reference": "#Practitioner1"}}],
        }
        self.assertDictEqual(self.imms, expected_output)

    def test_performing_professional_name(self):
        """Test that only non-empty performing_professional_name values are added"""
        # performing_professional: surname non-empty, _forename empty
        imms = copy.deepcopy(self.imms)
        _decorate_performer(imms, {"PERFORMING_PROFESSIONAL_SURNAME": "a_prof_surname"})
        self.assertListEqual(imms["contained"][0]["name"], [{"family": "a_prof_surname"}])

        # performing_professional: surname empty, _forename non-empty
        imms = copy.deepcopy(self.imms)
        headers = {"PERFORMING_PROFESSIONAL_FORENAME": "a_prof_forename"}
        _decorate_performer(imms, headers)
        self.assertListEqual(imms["contained"][0]["name"], [{"given": ["a_prof_forename"]}])

    def test_site_code(self):
        """Test that only non-empty site_code values are added"""
        # site_code non-empty, site_code_type_uri empty
        imms = copy.deepcopy(self.imms)
        _decorate_performer(imms, {"SITE_CODE": "a_site_code", "SITE_CODE_TYPE_URI": ""})
        self.assertDictEqual(imms["performer"][0]["actor"]["identifier"], {"value": "a_site_code"})

        # site_code empty, site_code_type_uri non-empty
        imms = copy.deepcopy(self.imms)
        _decorate_performer(imms, {"SITE_CODE": "", "SITE_CODE_TYPE_URI": "a_site_code_uri"})
        self.assertDictEqual(imms["performer"][0]["actor"]["identifier"], {"system": "a_site_code_uri"})

    def test_location(self):
        """Test that only non-empty location values are added"""
        # location_code non-empty, location_code_type_uri empty
        imms = copy.deepcopy(self.imms)
        headers = {"LOCATION_CODE": "a_location_code", "LOCATION_CODE_TYPE_URI": ""}
        _decorate_performer(imms, headers)
        self.assertDictEqual(imms["location"], {"type": "Location", "identifier": {"value": "a_location_code"}})

        # location_code empty, location_code_type_uri non-empty
        imms = copy.deepcopy(self.imms)
        headers = {"LOCATION_CODE": "", "LOCATION_CODE_TYPE_URI": "a_location_code_uri"}
        _decorate_performer(imms, headers)
        self.assertDictEqual(imms["location"], {"type": "Location", "identifier": {"system": "a_location_code_uri"}})


class TestProtocolAppliedDecorator(unittest.TestCase):
    """Tests for _decorate_vaccination"""

    def test_map_target_disease(self):
        """
        Test that map_target_disease maps each vaccine type to the correct targetDisease element containing all of
        the relevant disease codes
        """
        # NOTE: TEST CASES SHOULD INCLUDE ALL VACCINE TYPES WHICH ARE VALID FOR THIS PRODUCT.
        # A NEW TEST CASE SHOULD BE ADDED EVERY TIME THERE IS A VACCINE TYPE UPLIFT.

        # Test case tuples are structured (vaccine_type, expected_output)
        test_cases = [("covid19", COVID_19_TARGET_DISEASE_ELEMENT)]

        for vaccine_type, expected_output in test_cases:
            with self.subTest():
                self.assertEqual(map_target_disease(vaccine_type), expected_output)

    def test_protocol_applied_decorator(self):
        """Tests that _decorate_protocol_applied gives the correct output based on the input values"""
        valid_dose_sequence_expected_output = {
            **copy.deepcopy(raw_imms),
            "protocolApplied": [{"targetDisease": COVID_19_TARGET_DISEASE_ELEMENT, "doseNumberPositiveInt": 4}],
        }

        # TODO: Add other test cases once string, empty and more than 9 scenarios are confirmed
        # Test case tuples are structured as (test_name, row_data, expected_output)
        test_cases = [("DOSE_SEQUENCE integer 1 to 9", {"DOSE_SEQUENCE": "4"}, valid_dose_sequence_expected_output)]

        for test_name, row_data, expected_output in test_cases:
            with self.subTest(test_name):
                imms = copy.deepcopy(raw_imms)
                _decorate_protocol_applied(imms, row_data, "covid19")
                self.assertEqual(imms, expected_output)

    # def test_all_performer_headers(self):
    #     """Test that all performer fields are added when all performer fields contain non-empty data"""
    #     _decorate_performer(self.imms, AllHeaders.performer)
    #     self.assertDictEqual(self.imms, AllHeadersExpectedOutput.performer)

    # def test_no_performer_headers(self):
    #     """Test that no fields are added when no performer fields contain non-empty data"""
    #     _decorate_performer(self.imms, {})
    #     self.assertDictEqual(self.imms, {"resourceType": "Immunization", "contained": [], "status": "completed"})

    # def test_one_performer_header(self):
    #     """Test that the relevant fields are added when one performer field contains non-empty data"""
    #     _decorate_performer(self.imms, {"site_code": "a_site_code"})
    #     expected_output = {
    #         "resourceType": "Immunization",
    #         "status": "completed",
    #         "contained": [],
    #         "performer": [{"actor": {"type": "Organization", "identifier": {"value": "a_site_code"}}}],
    #     }
    #     self.assertDictEqual(self.imms, expected_output)
