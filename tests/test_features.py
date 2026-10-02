"""Protect the shared training/prediction input contract."""

import copy
import json
import unittest

from pilot.features import FEATURE_SETS, MISSING_CATEGORY, feature_contract, prepare_input, prepare_target
from pilot.identity import load_catalogue
from pilot.paths import PROJECT_ROOT


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = load_catalogue(PROJECT_ROOT / "catalogues/cars.json")
        self.scope = json.loads((PROJECT_ROOT / "configs/pilot_scope.json").read_text(encoding="utf-8"))
        self.row = {
            "make": " toyota ", "model": "COROLLA", "variant": "gli 1.3 vvti",
            "year": "2013.0", "mileage_km": "0", "listing_city": " lahore ",
            "engine_cc": "1300.0", "fuel": "cng", "transmission": "manual",
            "assembly": "local", "body_type": "N/A", "price_pkr": "3350000",
        }

    def test_training_row_and_prediction_form_have_identical_ordered_inputs(self):
        original = copy.deepcopy(self.row)
        prediction = {key: value for key, value in self.row.items() if key != "price_pkr"}
        prediction.update(listing_id="not-a-feature", registration_year="2000", year_meaning="different", source_url="ignored")
        for name, fields in FEATURE_SETS.items():
            train = prepare_input(self.row, name, self.catalogue, self.scope)
            infer = prepare_input(prediction, name, self.catalogue, self.scope)
            self.assertEqual(train, infer)
            self.assertEqual(tuple(train), fields)
            self.assertEqual(train["mileage_km"], 0)
            self.assertEqual(train["listing_city"], "Lahore")
            self.assertNotIn("price_pkr", train)
        self.assertEqual(self.row, original)
        self.assertEqual(prepare_target(self.row), 3350000)

    def test_optional_missing_values_are_consistent_and_unspecified_is_not_base(self):
        row = {**self.row, "variant": "", "fuel": None, "engine_cc": "", "body_type": "N/A"}
        result = prepare_input(row, "F2", self.catalogue, self.scope)
        self.assertEqual(result["variant"], MISSING_CATEGORY)
        self.assertEqual(result["body_type"], MISSING_CATEGORY)
        self.assertEqual(result["fuel"], MISSING_CATEGORY)
        self.assertIsNone(result["engine_cc"])
        self.assertEqual(feature_contract()["target_unit"], "PKR")

    def test_invalid_required_inputs_unknown_identity_and_invalid_optional_number_fail(self):
        for changes in [
            {"year": "2009"}, {"year": True}, {"mileage_km": "-1"},
            {"mileage_km": "NaN"}, {"mileage_km": "10.5"}, {"listing_city": ""},
            {"make": "unknown"}, {"variant": "GLi mystery edition"}, {"engine_cc": "0"},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                prepare_input({**self.row, **changes}, "F2", self.catalogue, self.scope)
        with self.assertRaises(ValueError):
            prepare_input(self.row, "F3", self.catalogue, self.scope)

    def test_target_is_separate_and_fuel_trim_semantics_are_preserved(self):
        row = {**self.row, "price_pkr": "invalid", "fuel": "phev"}
        inputs = prepare_input(row, "F2", self.catalogue, self.scope)
        self.assertEqual(inputs["fuel"], "PHEV")
        self.assertEqual(inputs["variant"], "GLi 1.3 VVTi")
        with self.assertRaises(ValueError):
            prepare_target(row)


if __name__ == "__main__":
    unittest.main()
