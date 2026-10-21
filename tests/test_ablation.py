"""Verify removed inputs, paired rules, references, and development isolation."""

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from pilot.ablation import REMOVALS, check_reference, read_config, read_csv, run_ablation
from pilot.ablation_report import summarize_ablation, within_limit
from pilot.comparison import compare_candidate, run_comparison
from pilot.evaluate import load_evaluation_data, sha256
from pilot.features import FEATURE_SETS
from pilot.metrics import regression_metrics
from pilot.models import build_candidate, input_frame
from pilot.paths import PROJECT_ROOT
import tests.test_comparison as comparison_tests


class AblationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.dataset, cls.evaluation = comparison_tests.ComparisonTests().create_artifacts(cls.root)
        comparison = json.loads((PROJECT_ROOT / "configs/experiments_modeling_002_reviewed.json").read_text())
        comparison["candidates"]["random_forest"]["n_estimators"] = 3
        comparison["candidates"]["catboost"]["iterations"] = 3
        comparison_path = cls.root / "comparison.json"
        comparison_path.write_text(json.dumps(comparison))
        cls.reference = cls.root / "reference"
        with contextlib.redirect_stdout(io.StringIO()):
            run_comparison(cls.dataset, cls.evaluation, cls.reference, comparison_path)
        cls.config = json.loads((PROJECT_ROOT / "configs/ablations_modeling_002.json").read_text())
        cls.config["candidates"] = {name: comparison["candidates"][name] for name in cls.config["candidates"]}
        cls.config_path = cls.root / "ablation.json"
        cls.config_path.write_text(json.dumps(cls.config))

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_invalid_column_subsets_never_build_a_frame_or_model(self):
        for columns in ([], ["year", "year"], ["price_pkr"], ["listing_id"], ["registration_year"], ["year", "make"]):
            for call in (lambda: input_frame([], "F2", columns=columns),
                         lambda: build_candidate("catboost", "F2", {}, 42, columns=columns)):
                with self.subTest(columns=columns), self.assertRaises(ValueError):
                    call()

    def test_dropped_city_never_reaches_either_estimator_or_encoder(self):
        data = load_evaluation_data(self.dataset, self.evaluation, "F2")
        columns = tuple(field for field in FEATURE_SETS["F2"] if field != "listing_city")
        frame = input_frame(data.inputs, "F2", columns=columns)
        self.assertNotIn("listing_city", frame)
        for name, parameters in self.config["candidates"].items():
            model = build_candidate(name, "F2", parameters, 42, columns=columns).fit(frame, np.asarray(data.targets))
            names = model.feature_names_ if name == "catboost" else model.feature_names_in_
            self.assertEqual(list(names), list(columns))
            if name == "random_forest":
                categories = model.named_steps["preprocess"].transformers_[1][2]
                self.assertNotIn("listing_city", categories)
            changed = [dict(row, listing_city="Entirely different") for row in data.inputs]
            np.testing.assert_array_equal(model.predict(frame), model.predict(input_frame(changed, "F2", columns=columns)))

    def test_config_rejects_metadata_targets_changed_matrix_and_invalid_limits(self):
        bad_configs = []
        for field in ("price_pkr", "listing_id", "registration_year", "make"):
            config = copy.deepcopy(self.config)
            config["remove_individually"][0] = field
            bad_configs.append(config)
        for value in (-1, float("nan"), True):
            config = copy.deepcopy(self.config)
            config["max_mae_increase_pct"]["overall"] = value
            bad_configs.append(config)
        for config in bad_configs:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "config.json"
                path.write_text(json.dumps(config))
                with self.assertRaises(ValueError):
                    read_config(path)

    def test_unrounded_limit_boundaries_and_zero_error(self):
        for limit in (1, 3, 5):
            self.assertTrue(within_limit(100 + limit, 100, limit))
            self.assertFalse(within_limit(100 + limit + 0.00001, 100, limit))
        self.assertTrue(within_limit(0, 0, 1))
        self.assertFalse(within_limit(0.00001, 0, 1))

    def test_family_and_fold_guards_can_block_an_overall_pass(self):
        config = {**self.config, "remove_individually": ["listing_city"], "candidates": {"catboost": {}}}
        for errors, passes in (([101]*6, True), ([108, 99, 99, 100, 99, 99], False), ([106]*3+[94]*3, False)):
            predictions, folds, fitted = [], [], []
            for experiment, values in (("catboost_full", [100]*6), ("catboost_without_listing_city", errors)):
                for index, error in enumerate(values):
                    predictions.append({"experiment": experiment, "fold": index % 3, "family": "A" if index < 3 else "B",
                                        "variant": "V", "year": 2020, "listing_city": "City", "unseen_city": False,
                                        "unseen_variant": False, "actual_pkr": 1000, "predicted_pkr": 1000+error})
                for fold in range(3):
                    estimates = [1000+value for index, value in enumerate(values) if index % 3 == fold]
                    folds.append({"experiment": experiment, "fold": fold, "fit_seconds": 0,
                                  **regression_metrics([1000]*2, estimates)})
                fitted.append({"experiment": experiment, "input_columns": ["make", "model"]})
            summary, _, _ = summarize_ablation(predictions, folds, fitted, config)
            self.assertTrue(summary[1]["overall_pass"])
            self.assertEqual(summary[1]["candidate_for_removal"], passes)

    def test_reference_mismatch_is_detected(self):
        data = load_evaluation_data(self.dataset, self.evaluation, "F2")
        rows, _, _ = compare_candidate(data, data.inputs, "F2", "random_forest", self.config["candidates"]["random_forest"], 42)
        old = read_csv(self.reference / "predictions.csv")
        check_reference("random_forest", rows, old, data, 0.01)
        changed = copy.deepcopy(rows)
        changed[0]["predicted_pkr"] += 0.02
        with self.assertRaisesRegex(ValueError, "did not reproduce"):
            check_reference("random_forest", changed, old, data, 0.01)

    def test_end_to_end_preserves_inputs_metadata_and_exact_development_folds(self):
        output = self.root / "ablation"
        originals = {path: path.read_bytes() for root in (self.dataset, self.evaluation, self.reference) for path in root.iterdir()}
        with patch("pilot.ablation.load_evaluation_data", wraps=load_evaluation_data) as loader, contextlib.redirect_stdout(io.StringIO()):
            manifest = run_ablation(self.dataset, self.evaluation, self.reference, output, self.config_path)
        loader.assert_called_once_with(self.dataset.resolve(), self.evaluation.resolve(), "F2")
        assignments = json.loads((self.evaluation / "splits.json").read_text())["assignments"]
        by_id = {item["listing_id"]: item for item in assignments}
        development = {key for key, item in by_id.items() if item["partition"] == "development"}
        predictions = read_csv(output / "predictions.csv")
        details = json.loads((output / "fold_details.json").read_text())
        self.assertEqual(len(predictions), len(development)*20)
        self.assertEqual(len(details), 60)
        for experiment in {row["experiment"] for row in predictions}:
            rows = [row for row in predictions if row["experiment"] == experiment]
            self.assertEqual({row["listing_id"] for row in rows}, development)
            self.assertEqual(len(rows), len(development))
            for row in rows:
                self.assertEqual(int(row["fold"]), by_id[row["listing_id"]]["validation_fold"])
                self.assertEqual(row["listing_city"], "Lahore")
        for item in details:
            train, val = set(item["training_ids"]), set(item["validation_ids"])
            self.assertFalse(train & val)
            self.assertEqual(train | val, development)
            self.assertFalse({by_id[key]["group_id"] for key in train} & {by_id[key]["group_id"] for key in val})
            if "_without_" in item["experiment"]:
                removed = item["experiment"].split("_without_")[1]
                self.assertEqual(item["input_columns"], [field for field in FEATURE_SETS["F2"] if field != removed])
        for path, content in originals.items():
            self.assertEqual(path.read_bytes(), content)
        for name, fingerprint in manifest["output_sha256"].items():
            self.assertEqual(sha256(output / name), fingerprint)
        for rejected in (output, self.dataset / "nested", self.evaluation / "nested", self.reference / "nested", PROJECT_ROOT / "data/raw/ablation_test"):
            with self.assertRaises(ValueError):
                run_ablation(self.dataset, self.evaluation, self.reference, rejected, self.config_path)

    def test_reference_parameter_drift_stops_before_fitting(self):
        config = copy.deepcopy(self.config)
        config["candidates"]["catboost"]["depth"] += 1
        path = self.root / "changed_config.json"
        path.write_text(json.dumps(config))
        with patch("pilot.ablation.compare_candidate") as compare, self.assertRaisesRegex(ValueError, "preserve reference"):
            run_ablation(self.dataset, self.evaluation, self.reference, self.root / "bad_run", path)
        compare.assert_not_called()
        self.assertFalse((self.root / "bad_run").exists())

    def test_combined_config_accepts_only_the_selected_pair_without_mixed_modes(self):
        config = json.loads((PROJECT_ROOT / "configs/ablations_modeling_002_combined.json").read_text())
        path = self.root / "combined_validation.json"
        path.write_text(json.dumps(config))
        self.assertEqual(read_config(path)["remove_together"], ["fuel", "body_type"])
        for fields in (["fuel"], ["fuel", "listing_city"], ["fuel", "fuel"], ["price_pkr", "body_type"]):
            changed = {**config, "remove_together": fields}
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                read_config(path)
        path.write_text(json.dumps({**config, "remove_individually": list(REMOVALS)}))
        with self.assertRaises(ValueError):
            read_config(path)

    def test_combined_end_to_end_omits_both_fields_and_preserves_folds(self):
        config = json.loads((PROJECT_ROOT / "configs/ablations_modeling_002_combined.json").read_text())
        config["candidates"] = self.config["candidates"]
        path, output = self.root / "combined.json", self.root / "combined"
        path.write_text(json.dumps(config))
        originals = {p: p.read_bytes() for root in (self.dataset, self.evaluation, self.reference) for p in root.iterdir()}
        with patch("pilot.ablation.load_evaluation_data", wraps=load_evaluation_data) as loader, contextlib.redirect_stdout(io.StringIO()):
            manifest = run_ablation(self.dataset, self.evaluation, self.reference, output, path)
        loader.assert_called_once_with(self.dataset.resolve(), self.evaluation.resolve(), "F2")
        data = load_evaluation_data(self.dataset, self.evaluation, "F2")
        details = json.loads((output / "fold_details.json").read_text())
        self.assertEqual(manifest["configurations"], 4)
        self.assertEqual(len(details), 12)
        predictions = read_csv(output / "predictions.csv")
        self.assertEqual(len(predictions), len(data.targets)*4)
        for item in details:
            removed = ("fuel", "body_type") if "_without_" in item["experiment"] else ()
            self.assertEqual(item["input_columns"], [field for field in FEATURE_SETS["F2"] if field not in removed])
            train, val = set(item["training_ids"]), set(item["validation_ids"])
            self.assertFalse(train & val)
            self.assertEqual(train | val, set(data.listing_ids))
        for experiment in {row["experiment"] for row in predictions}:
            rows = [row for row in predictions if row["experiment"] == experiment]
            self.assertEqual(len(rows), len(data.targets))
            for row in rows:
                index = data.listing_ids.index(row["listing_id"])
                self.assertEqual(int(row["fold"]), data.validation_folds[index])
                self.assertEqual(float(row["actual_pkr"]), data.targets[index])
        report = (output / "ablation_report.md").read_text()
        self.assertIn("Joint fuel/body-type removal", report)
        self.assertNotIn("City removal qualifies", report)
        for p, content in originals.items():
            self.assertEqual(p.read_bytes(), content)
        for name, value in manifest["output_sha256"].items():
            self.assertEqual(sha256(output / name), value)


if __name__ == "__main__":
    unittest.main()
