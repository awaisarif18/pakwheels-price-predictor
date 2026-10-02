"""Protect deterministic membership, group isolation, and frozen evaluation loading."""

import copy
import csv
import json
import tempfile
import unittest
from pathlib import Path

from pilot.evaluate import POPULATION, load_evaluation_data, sha256
from pilot.features import FEATURE_SETS
from pilot.identity import load_catalogue
from pilot.paths import PROJECT_ROOT
from pilot.splits import build_splits, validate_splits
from scripts.prepare_evaluation import prepare_evaluation


class SplitTests(unittest.TestCase):
    def setUp(self):
        self.config_path = PROJECT_ROOT / "configs/evaluation_pilot.json"
        self.catalogue_path = PROJECT_ROOT / "catalogues/cars.json"
        self.scope_path = PROJECT_ROOT / "configs/pilot_scope.json"
        self.config = json.loads(self.config_path.read_text(encoding="utf-8"))
        catalogue = load_catalogue(self.catalogue_path)
        self.rows = []
        for family_index, family in enumerate(catalogue["families"]):
            for index in range(8):
                listing_id = f"{family_index}{index}"
                self.rows.append({
                    "listing_id": listing_id, "group_id": f"vehicle_{listing_id}",
                    "make": family["make"], "model": family["model"], "variant": family["variants"][0],
                    "year": "2020", "mileage_km": str(index * 1000), "listing_city": "Lahore",
                    "price_pkr": str(1000000 + index), "fuel": "Petrol", "engine_cc": "1300",
                    "transmission": "Manual", "assembly": "Local", "body_type": "Sedan",
                    "source_checked_candidate": "True", "source_price_verified": "True", "exclusion_reasons": "",
                })

    def test_input_order_and_prices_cannot_change_assignments(self):
        first = build_splits(self.rows, self.config)
        changed = [{**row, "price_pkr": "999999999"} for row in reversed(self.rows)]
        self.assertEqual(first, build_splits(changed, self.config))
        self.assertNotEqual(first["assignments"], build_splits(self.rows, {**self.config, "seed": 43})["assignments"])
        self.assertEqual(sum(item["partition"] == "demo_test" for item in first["assignments"]), 8)

    def test_reposts_stay_together_and_validation_excludes_test_and_training_groups(self):
        rows = self.rows + [{**self.rows[0], "listing_id": "repost"}]
        splits = build_splits(rows, self.config)
        by_id = {item["listing_id"]: item for item in splits["assignments"]}
        self.assertEqual(by_id["00"]["partition"], by_id["repost"]["partition"])
        self.assertEqual(by_id["00"]["validation_fold"], by_id["repost"]["validation_fold"])
        test = {item["group_id"] for item in splits["assignments"] if item["partition"] == "demo_test"}
        for fold in range(3):
            validation = {item["group_id"] for item in splits["assignments"] if item["partition"] == "development" and item["validation_fold"] == fold}
            training = {item["group_id"] for item in splits["assignments"] if item["partition"] == "development" and item["validation_fold"] != fold}
            self.assertTrue(validation)
            self.assertFalse(validation & training or test & (validation | training))

    def test_duplicate_cross_family_and_insufficient_groups_fail(self):
        for rows in [
            self.rows + [self.rows[0]],
            self.rows + [{**self.rows[8], "listing_id": "cross", "group_id": self.rows[0]["group_id"]}],
            self.rows[:3], [],
        ]:
            with self.subTest(size=len(rows)), self.assertRaises(ValueError):
                build_splits(rows, self.config)

    def test_saved_assignments_reject_omissions_and_group_leakage(self):
        rows = self.rows + [{**self.rows[0], "listing_id": "repost"}]
        original = build_splits(rows, self.config)
        omitted = copy.deepcopy(original)
        omitted["assignments"].pop()
        with self.assertRaisesRegex(ValueError, "omits"):
            validate_splits(rows, omitted)
        leaked = copy.deepcopy(original)
        item = next(item for item in leaked["assignments"] if item["listing_id"] == "repost")
        source = next(item for item in leaked["assignments"] if item["listing_id"] == "00")
        item["partition"] = "development" if source["partition"] == "demo_test" else "demo_test"
        item["validation_fold"] = 0 if item["partition"] == "development" else None
        with self.assertRaisesRegex(ValueError, "leakage"):
            validate_splits(rows, leaked)

    def test_artifact_roundtrip_aligns_all_features_and_refuses_overwrite_or_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset, output = Path(directory) / "dataset", Path(directory) / "evaluation"
            dataset.mkdir()
            with (dataset / POPULATION).open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(self.rows[0]))
                writer.writeheader()
                writer.writerows(reversed(self.rows))
            manifest = {
                "preparation_schema_version": 1, "dataset_id": "synthetic", "source_checked_candidates": len(self.rows),
                "output_sha256": {POPULATION: sha256(dataset / POPULATION)},
                "input_fingerprints": {"catalogue_sha256": sha256(self.catalogue_path), "scope_sha256": sha256(self.scope_path)},
            }
            (dataset / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            original = (dataset / POPULATION).read_bytes()
            created = prepare_evaluation(dataset, output, self.config_path, self.catalogue_path, self.scope_path)
            baseline = load_evaluation_data(dataset, output, "F0")
            for name in FEATURE_SETS:
                data = load_evaluation_data(dataset, output, name)
                self.assertEqual(data.listing_ids, baseline.listing_ids)
                self.assertEqual(data.targets, baseline.targets)
                self.assertEqual(data.validation_folds, baseline.validation_folds)
                self.assertEqual(len(data.inputs), 24)
                self.assertNotIn("group_id", data.inputs[0])
            test = load_evaluation_data(dataset, output, "F0", partition="demo_test")
            self.assertEqual(len(test.inputs), 8)
            self.assertFalse(set(test.listing_ids) & set(baseline.listing_ids))
            self.assertEqual((dataset / POPULATION).read_bytes(), original)
            # Identical inputs/code produce the same split ID and assignment bytes.
            second = Path(directory) / "evaluation_copy"
            again = prepare_evaluation(dataset, second, self.config_path, self.catalogue_path, self.scope_path)
            self.assertEqual(created["split_id"], again["split_id"])
            self.assertEqual((output / "splits.json").read_bytes(), (second / "splits.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "already exists"):
                prepare_evaluation(dataset, output, self.config_path, self.catalogue_path, self.scope_path)
            (output / "splits.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                load_evaluation_data(dataset, output, "F0")
            (dataset / POPULATION).write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "changed"):
                load_evaluation_data(dataset, second, "F0")


if __name__ == "__main__":
    unittest.main()
