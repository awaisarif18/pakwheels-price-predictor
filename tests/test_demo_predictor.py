"""Frozen selection, bounded saved inference, and one-time holdout use."""

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pilot.comparison import save_csv
from pilot.demo_artifacts import finish_artifact, input_hashes, read_json, save_json, usage_path
from pilot.demo_evaluation import evaluate_demo
from pilot.demo_release import require_qualified_demo
from pilot.evaluate import load_evaluation_data, sha256
from pilot.paths import PROJECT_ROOT
from pilot.predictor import SavedPredictor, check_examples, train_demo
from pilot.predictor_inputs import load_predictor_contract, load_predictor_development
from pilot.qualification import error_report, qualify_demo
from pilot.support import build_support, family_name, support_reason
import tests.test_comparison as comparison_tests


class DemoPredictorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.dataset, cls.evaluation = comparison_tests.ComparisonTests().create_artifacts(cls.root)
        cls.data = load_predictor_development(cls.dataset, cls.evaluation)
        cls.policy = read_json(PROJECT_ROOT / "configs/demo_qualification_v1.json")
        cls.policy["parameters"]["iterations"] = 3
        cls.policy["coverage"].update(min_family_groups=3, min_variant_groups=2, min_family_year_groups=1, min_family_city_groups=1)
        cls.policy.update(development_min_supported_family_groups=2, test_min_supported_rows=4, test_min_supported_family_rows=1)
        cls.policy["errors"].update(overall_mae_pkr=1000000, median_ape_pct=100,
                                    family_mae_pkr={name: 1000000 for name in cls.policy["errors"]["family_mae_pkr"]})
        cls.policy_path = cls.root / "policy.json"
        save_json(cls.policy_path, cls.policy)
        cls.evidence, cls.baseline = cls.root / "evidence", cls.root / "baseline"
        for directory, experiment, error in ((cls.evidence, cls.policy["experiment"], 10000),
                                              (cls.baseline, cls.policy["baseline_experiment"], 100000)):
            directory.mkdir()
            rows = []
            for i, row in enumerate(cls.data.inputs):
                rows.append({"listing_id": cls.data.listing_ids[i], "group_id": cls.data.group_ids[i],
                             "experiment": experiment, "family": family_name(row), "fold": cls.data.validation_folds[i],
                             "actual_pkr": cls.data.targets[i], "predicted_pkr": cls.data.targets[i]+error})
            save_csv(directory / "predictions.csv", rows)
            save_json(directory / "config.json", {"seed": cls.policy["seed"], "target": "raw_pkr",
                      "candidates": {"catboost": cls.policy["parameters"]}})
            save_json(directory / "fold_details.json", [{"experiment": experiment, "input_columns": load_predictor_contract()["columns"]}]*3)
            finish_artifact(directory, {"test_status": "reserved_unopened_for_model_outcomes"},
                            input_hashes([cls.dataset / "manifest.json", cls.evaluation / "manifest.json"]), ())
        cls.qualification, cls.bundle = cls.root / "qualification", cls.root / "bundle"
        cls.usage = cls.root / "usage"
        qualify_demo(cls.dataset, cls.evaluation, cls.evidence, cls.baseline, cls.qualification, cls.policy_path, usage_dir=cls.usage)
        train_demo(cls.dataset, cls.evaluation, cls.qualification, cls.bundle)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_scope_uses_groups_and_attributes_without_targets(self):
        first = build_support(self.data, self.policy)
        changed = replace(self.data, targets=tuple(-999999 for _ in self.data.targets))
        self.assertEqual(first, build_support(changed, self.policy))
        with self.assertRaisesRegex(ValueError, "No variants"):
            build_support(replace(self.data, group_ids=tuple("one_vehicle" for _ in self.data.group_ids)), self.policy)

    def test_support_rejects_unknown_combinations_and_extrapolation(self):
        support = read_json(self.bundle / "support.json")
        row = next(row for row in self.data.inputs if support_reason(row, support) is None)
        for changes in ({"variant": "unseen"}, {"year": 2100}, {"listing_city": "unseen"},
                        {"mileage_km": -1}, {"engine_cc": 9999}, {"transmission": "unknown"}):
            self.assertIsNotNone(support_reason({**row, **changes}, support))

    def test_error_limits_can_fail_even_with_sufficient_rows(self):
        candidate = [{"listing_id": str(i), "family": family, "actual_pkr": 1000000, "predicted_pkr": 1010000}
                     for i, family in enumerate(self.policy["errors"]["family_mae_pkr"])]
        baseline = {row["listing_id"]: {**row, "predicted_pkr": 1100000} for row in candidate}
        self.assertTrue(error_report(candidate, baseline, self.policy, 4, 1)["passed"])
        candidate[0]["predicted_pkr"] = 4000000
        self.assertFalse(error_report(candidate, baseline, self.policy, 4, 1)["passed"])
        self.assertFalse(error_report([], baseline, self.policy, 4, 1)["passed"])

    def test_qualification_never_requests_reserved_partition_and_preserves_inputs(self):
        output = self.root / "qualification_again"
        originals = {p: p.read_bytes() for root in (self.dataset, self.evaluation, self.evidence, self.baseline) for p in root.iterdir()}
        with patch("pilot.predictor_inputs.load_evaluation_data", wraps=load_evaluation_data) as loader:
            result = qualify_demo(self.dataset, self.evaluation, self.evidence, self.baseline, output, self.policy_path, usage_dir=self.usage)
        self.assertEqual(result["status"], "qualified_development")
        loader.assert_called_once_with(self.dataset, self.evaluation, "F2")
        for p, value in originals.items():
            self.assertEqual(p.read_bytes(), value)

    def test_native_model_roundtrip_and_examples(self):
        self.assertEqual(check_examples(self.bundle), 4)
        predictor = SavedPredictor(self.bundle)
        form = read_json(self.bundle / "example_input.json")
        prediction = predictor.predict(form)
        self.assertGreater(prediction["price_pkr"], 0)
        self.assertEqual(predictor.model.feature_names_, load_predictor_contract()["columns"])
        self.assertEqual(prediction, predictor.predict({**form, "fuel": "ignored", "body_type": "ignored", "registration_year": 1900}))
        with self.assertRaises(ValueError):
            predictor.predict({**form, "mileage_km": 99999999})

    def test_failed_qualification_and_overwrites_cannot_train(self):
        with self.assertRaises(ValueError):
            train_demo(self.dataset, self.evaluation, self.qualification, self.bundle)
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "failed"
            fake.mkdir()
            save_json(fake / "manifest.json", {"status": "failed_development", "input_sha256": {}, "output_sha256": {}})
            with self.assertRaisesRegex(ValueError, "must pass"):
                train_demo(self.dataset, self.evaluation, fake, Path(directory) / "output")

    def test_saved_weight_tampering_is_refused(self):
        import shutil
        changed = self.root / "tampered"
        shutil.copytree(self.bundle, changed)
        with (changed / "model.cbm").open("ab") as handle:
            handle.write(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            SavedPredictor(changed)

    def test_final_test_is_once_only_and_cannot_redefine_scope_afterward(self):
        usage = self.root / "once_usage"
        output = self.root / "test_once"
        originals = {p: p.read_bytes() for root in (self.dataset, self.evaluation, self.bundle) for p in root.iterdir()}
        result = evaluate_demo(self.dataset, self.evaluation, self.bundle, output, usage_dir=usage)
        report = read_json(output / "metrics.json")
        self.assertEqual(report["reserved_test_rows"], 8)
        self.assertEqual(result["test_status"], "opened_scored_frozen_candidate")
        self.assertEqual(read_json(usage_path(result["split_id"], usage))["status"], "completed")
        for p, value in originals.items():
            self.assertEqual(p.read_bytes(), value)
        with self.assertRaisesRegex(ValueError, "already been opened"):
            evaluate_demo(self.dataset, self.evaluation, self.bundle, self.root / "test_twice", usage_dir=usage)
        with self.assertRaisesRegex(ValueError, "already been opened"):
            qualify_demo(self.dataset, self.evaluation, self.evidence, self.baseline, self.root / "reselected", self.policy_path, usage_dir=usage)

    def test_failed_scoring_still_records_test_usage(self):
        usage = self.root / "failure_usage"
        with patch("pilot.demo_evaluation.load_evaluation_data", side_effect=RuntimeError("scoring failed")):
            with self.assertRaisesRegex(RuntimeError, "scoring failed"):
                evaluate_demo(self.dataset, self.evaluation, self.bundle, self.root / "failed_scoring", usage_dir=usage)
        split_id = read_json(self.bundle / "manifest.json")["split_id"]
        self.assertEqual(read_json(usage_path(split_id, usage))["status"], "opened_scoring_started")

    def test_release_requires_passed_metrics_for_this_exact_bundle(self):
        output = self.root / "release_result"
        output.mkdir()
        details = {"kind": "demo_test", "split_id": read_json(self.bundle / "manifest.json")["split_id"],
                   "bundle_manifest_sha256": sha256(self.bundle / "manifest.json"), "passed": True}
        save_json(output / "metrics.json", {"passed": True, "checks": []})
        finish_artifact(output, details, {}, ())
        self.assertTrue(require_qualified_demo(self.bundle, output)["passed"])
        details["bundle_manifest_sha256"] = "different"
        (output / "manifest.json").unlink()
        finish_artifact(output, details, {}, ())
        with self.assertRaisesRegex(ValueError, "exact frozen"):
            require_qualified_demo(self.bundle, output)

    def test_release_refuses_missing_or_failed_final_evaluation(self):
        with self.assertRaisesRegex(ValueError, "no final"):
            require_qualified_demo(self.bundle, self.root / "missing_result")
        output = self.root / "failed_release"
        output.mkdir()
        save_json(output / "metrics.json", {"passed": False, "checks": [{"check": "family MAE", "passed": False}]})
        finish_artifact(output, {"kind": "demo_test", "passed": False,
                        "split_id": read_json(self.bundle / "manifest.json")["split_id"],
                        "bundle_manifest_sha256": sha256(self.bundle / "manifest.json")}, {}, ())
        with self.assertRaisesRegex(ValueError, "failed final.*family MAE"):
            require_qualified_demo(self.bundle, output)


if __name__ == "__main__":
    unittest.main()
