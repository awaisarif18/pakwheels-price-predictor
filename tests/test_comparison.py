"""Protect held-out fitting and a development-only, reproducible comparison ledger."""

import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from pilot.comparison import compare_candidate, fold_indices, run_comparison
from pilot.evaluate import EvaluationData, POPULATION, load_evaluation_data, sha256
from pilot.identity import load_catalogue
from pilot.models import ComparableMedian
from pilot.paths import PROJECT_ROOT
from scripts.prepare_evaluation import prepare_evaluation


class ComparisonTests(unittest.TestCase):
    def test_each_fit_is_fresh_and_has_no_validation_rows_or_targets(self):
        inputs = tuple({"make": "Honda", "model": "City", "year": 2020,
                        "mileage_km": index, "listing_city": "Lahore", "variant": "1.3"} for index in range(6))
        data = EvaluationData(tuple(map(str, range(6))), tuple(map(str, range(6))),
                              (0, 0, 1, 1, 2, 2), inputs, (100, 200, 300, 400, 500, 600))
        fitted_targets = []

        class RecordingMedian(ComparableMedian):
            def fit(self, frame, targets):
                fitted_targets.append(list(targets))
                return super().fit(frame, targets)

        with patch("pilot.comparison.build_candidate", side_effect=lambda *args: RecordingMedian(2)) as factory:
            rows, folds, _ = compare_candidate(data, inputs, "F0", "median", {"min_group_size": 2}, 42)
        self.assertEqual(factory.call_count, 3)
        self.assertEqual(fitted_targets, [[300, 400, 500, 600], [100, 200, 500, 600], [100, 200, 300, 400]])
        self.assertEqual(len({row["listing_id"] for row in rows}), 6)
        self.assertEqual([row["count"] for row in folds], [2, 2, 2])
        changed = EvaluationData(data.listing_ids, data.group_ids, data.validation_folds, inputs,
                                 (9999999, 9999999, 300, 400, 500, 600))
        changed_rows, _, _ = compare_candidate(changed, inputs, "F0", "median", {"min_group_size": 2}, 42)
        np.testing.assert_array_equal([row["predicted_pkr"] for row in rows if row["fold"] == 0],
                                      [row["predicted_pkr"] for row in changed_rows if row["fold"] == 0])
        leaking = EvaluationData(data.listing_ids, ("same", "1", "same", "3", "4", "5"),
                                 data.validation_folds, inputs, data.targets)
        with self.assertRaisesRegex(ValueError, "overlap"):
            list(fold_indices(leaking))

    def create_artifacts(self, root):
        catalogue_path = PROJECT_ROOT / "catalogues/cars.json"
        scope_path = PROJECT_ROOT / "configs/pilot_scope.json"
        rows = []
        for family_index, family in enumerate(load_catalogue(catalogue_path)["families"]):
            for index in range(8):
                listing_id = f"{family_index}{index}"
                rows.append({
                    "listing_id": listing_id, "group_id": f"vehicle_{listing_id}",
                    "make": family["make"], "model": family["model"], "variant": family["variants"][0],
                    "year": str(2015 + index), "mileage_km": str(index * 1000), "listing_city": "Lahore",
                    "price_pkr": str(1000000 + family_index * 100000 + index * 10000),
                    "fuel": "Petrol", "engine_cc": "1300", "transmission": "Manual", "assembly": "Local",
                    "body_type": "Sedan", "source_checked_candidate": "True", "source_price_verified": "True", "exclusion_reasons": "",
                })
        dataset, evaluation = root / "dataset", root / "evaluation"
        dataset.mkdir()
        with (dataset / POPULATION).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        manifest = {
            "preparation_schema_version": 1, "dataset_id": "synthetic", "source_checked_candidates": len(rows),
            "output_sha256": {POPULATION: sha256(dataset / POPULATION)},
            "input_fingerprints": {"catalogue_sha256": sha256(catalogue_path), "scope_sha256": sha256(scope_path)},
        }
        (dataset / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        prepare_evaluation(dataset, evaluation, PROJECT_ROOT / "configs/evaluation_pilot.json", catalogue_path, scope_path)
        return dataset, evaluation

    def test_end_to_end_never_requests_test_and_preserves_inputs_and_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, evaluation = self.create_artifacts(root)
            output, config_path = root / "comparison", root / "experiments.json"
            config = json.loads((PROJECT_ROOT / "configs/experiments.json").read_text())
            config["candidates"]["random_forest"]["n_estimators"] = 5
            config["candidates"]["catboost"]["iterations"] = 5
            config_path.write_text(json.dumps(config), encoding="utf-8")
            originals = {path: path.read_bytes() for source in (dataset, evaluation) for path in source.iterdir()}
            with patch("pilot.comparison.load_evaluation_data", wraps=load_evaluation_data) as loader, contextlib.redirect_stdout(io.StringIO()):
                manifest = run_comparison(dataset, evaluation, output, config_path)
            self.assertEqual(loader.call_count, 3)
            for call in loader.call_args_list:
                self.assertEqual(len(call.args), 3)
                self.assertNotIn("partition", call.kwargs)
            splits = json.loads((evaluation / "splits.json").read_text())
            test_ids = {row["listing_id"] for row in splits["assignments"] if row["partition"] == "demo_test"}
            with (output / "predictions.csv").open(newline="") as handle:
                predictions = list(csv.DictReader(handle))
            self.assertEqual(len(predictions), 24 * 12)
            self.assertFalse(test_ids & {row["listing_id"] for row in predictions})
            for feature_set in ("F0", "F1", "F2"):
                rows = [row for row in predictions if row["experiment"] == f"median_{feature_set}"]
                self.assertEqual(len({row["listing_id"] for row in rows}), 24)
            for path, original in originals.items():
                self.assertEqual(path.read_bytes(), original)
            for name, fingerprint in manifest["output_sha256"].items():
                self.assertEqual(sha256(output / name), fingerprint)
            for rejected in (output, dataset / "nested", evaluation / "nested", PROJECT_ROOT / "data/raw/comparison_test"):
                with self.assertRaises(ValueError):
                    run_comparison(dataset, evaluation, rejected, config_path)
            self.assertEqual(len(json.loads((output / "fold_details.json").read_text())), 36)


if __name__ == "__main__":
    unittest.main()
