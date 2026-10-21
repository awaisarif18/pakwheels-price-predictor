"""Guard the adopted predictor's shared inputs and preserved evaluation history."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from pilot.evaluate import load_evaluation_data
from pilot.features import FEATURE_SETS, MISSING_CATEGORY, feature_contract, prepare_input
from pilot.identity import load_catalogue
from pilot.paths import PROJECT_ROOT
from pilot.predictor_inputs import (
    PREDICTOR_COLUMNS, build_predictor_candidate, load_predictor_contract,
    load_predictor_development, predictor_frame, prepare_predictor_input,
)
import tests.test_comparison as comparison_tests


class PredictorInputTests(unittest.TestCase):
    def setUp(self):
        self.contract = load_predictor_contract()
        self.catalogue = load_catalogue(PROJECT_ROOT / "catalogues/cars.json")
        self.scope = json.loads((PROJECT_ROOT / "configs/pilot_scope.json").read_text())
        self.row = {"make": " toyota ", "model": "COROLLA", "variant": "gli 1.3 vvti", "year": "2013.0",
                    "mileage_km": "0", "listing_city": " lahore ", "transmission": "manual",
                    "engine_cc": "1300.0", "assembly": "local", "fuel": "Petrol", "body_type": "Sedan",
                    "registration_year": "2014", "price_pkr": "3350000"}

    def test_form_and_training_rows_match_without_reading_excluded_inputs(self):
        class GuardedRow(dict):
            def get(self, key, default=None):
                if key not in PREDICTOR_COLUMNS:
                    raise AssertionError(f"Read excluded input: {key}")
                return super().get(key, default)
        original = copy.deepcopy(self.row)
        training = prepare_predictor_input(GuardedRow(self.row), self.catalogue, self.scope)
        form = {field: self.row[field] for field in PREDICTOR_COLUMNS}
        self.assertEqual(training, prepare_predictor_input(form, self.catalogue, self.scope))
        self.assertEqual(tuple(training), PREDICTOR_COLUMNS)
        self.assertEqual(len(training), 9)
        self.assertEqual(training["mileage_km"], 0)
        self.assertEqual(training["listing_city"], "Lahore")
        self.assertEqual(self.row, original)

    def test_same_normalization_as_the_confirmed_experiment(self):
        before = feature_contract()
        full = prepare_input(self.row, "F2", self.catalogue, self.scope)
        reduced = prepare_predictor_input(self.row, self.catalogue, self.scope)
        self.assertEqual(reduced, {field: full[field] for field in PREDICTOR_COLUMNS})
        self.assertEqual(feature_contract(), before)
        self.assertIn("fuel", FEATURE_SETS["F2"])
        self.assertIn("body_type", FEATURE_SETS["F2"])

    def test_missing_optional_and_invalid_retained_values_keep_existing_rules(self):
        row = {**self.row, "variant": "", "transmission": None, "engine_cc": "", "assembly": "N/A"}
        prepared = prepare_predictor_input(row, self.catalogue, self.scope)
        self.assertIsNone(prepared["engine_cc"])
        for field in ("variant", "transmission", "assembly"):
            self.assertEqual(prepared[field], MISSING_CATEGORY)
        for change in ({"year": 2009}, {"mileage_km": -1}, {"listing_city": ""}, {"engine_cc": 0},
                       {"make": "unknown"}, {"variant": "unknown trim"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                prepare_predictor_input({**self.row, **change}, self.catalogue, self.scope)

    def test_changed_contracts_cannot_reintroduce_fields_or_drift_order_and_missingness(self):
        changes = [{"columns": list(PREDICTOR_COLUMNS)+[field]} for field in ("fuel", "body_type", "registration_year", "price_pkr")]
        changes += [{"columns": list(reversed(PREDICTOR_COLUMNS))}, {"numerical": ["year"]},
                    {"missing_category": ""}, {"contract_schema_version": 2}, {"target": "year"}]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "contract.json"
                changed = {**self.contract, **change}
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    load_predictor_contract(path)
                with self.assertRaises(ValueError):
                    build_predictor_candidate("catboost", {}, 42, contract=changed)

    def test_both_candidates_fit_and_predict_with_exactly_nine_inputs(self):
        rows = [{**self.row, "year": 2013+i, "mileage_km": i*10000} for i in range(8)]
        train = predictor_frame([prepare_predictor_input(row, self.catalogue, self.scope) for row in rows])
        forms = [{key: value for key, value in row.items() if key in PREDICTOR_COLUMNS} for row in rows]
        inference = predictor_frame([prepare_predictor_input(row, self.catalogue, self.scope) for row in forms])
        self.assertEqual(list(train.columns), list(PREDICTOR_COLUMNS))
        self.assertTrue(train.equals(inference))
        for name, parameters in {"catboost": {"iterations": 3, "depth": 2},
                                 "random_forest": {"n_estimators": 3, "min_samples_leaf": 2}}.items():
            model = build_predictor_candidate(name, parameters, 42).fit(train, np.arange(8)*100000+1000000)
            names = model.feature_names_ if name == "catboost" else model.feature_names_in_
            self.assertEqual(list(names), list(PREDICTOR_COLUMNS))
            np.testing.assert_array_equal(model.predict(train), model.predict(inference))

    def test_development_loader_preserves_folds_targets_groups_and_never_requests_test(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, evaluation = comparison_tests.ComparisonTests().create_artifacts(Path(directory))
            full = load_evaluation_data(dataset, evaluation, "F2")
            originals = {path: path.read_bytes() for root in (dataset, evaluation) for path in root.iterdir()}
            with patch("pilot.predictor_inputs.load_evaluation_data", wraps=load_evaluation_data) as loader:
                reduced = load_predictor_development(dataset, evaluation)
            loader.assert_called_once_with(dataset, evaluation, "F2")
            for field in ("listing_ids", "targets", "group_ids", "validation_folds"):
                self.assertEqual(getattr(full, field), getattr(reduced, field))
            for old, new in zip(full.inputs, reduced.inputs):
                self.assertEqual(tuple(new), PREDICTOR_COLUMNS)
                self.assertEqual(new, {field: old[field] for field in PREDICTOR_COLUMNS})
            frame = predictor_frame(reduced.inputs)
            self.assertEqual(tuple(frame.columns), PREDICTOR_COLUMNS)
            for path, content in originals.items():
                self.assertEqual(path.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
