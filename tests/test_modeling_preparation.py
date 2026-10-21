"""Offline round trip for consolidation, history-aware splits, and input hashes."""

from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pilot.audit import REQUIRED_COLUMNS
from pilot.evaluate import load_evaluation_data, sha256
from pilot.paths import PROJECT_ROOT
from scripts.prepare_dataset import write_csv
from scripts.prepare_evaluation import prepare_evaluation, save_json
from scripts.prepare_modeling_dataset import prepare_modeling_dataset


class ModelingPreparationTests(unittest.TestCase):
    def build_inputs(self, root):
        batch, parent = root / "batch", root / "parent"
        batch.mkdir()
        parent.mkdir()
        records = []
        for index in range(16):
            row = {field: "" for field in REQUIRED_COLUMNS}
            row.update(listing_id=str(index), car_title="Honda City 1.3 i-VTEC 2020", year="2020",
                       price_pkr=str(1000000 + index * 10000), mileage_km=str(index * 1000),
                       make="Honda", model="City", variant="1.3 i-VTEC", fuel="Petrol", transmission="Manual",
                       engine_cc="1300", listing_city="Lahore", assembly="Local", body_type="Sedan",
                       collected_at="2026-10-17T00:00:00+00:00", parse_status="complete",
                       source_url=f"https://www.pakwheels.com/used-cars/city-2020-for-sale-in-lahore-{index}")
            records.append(row)
        for name in ("pakwheels_raw.csv", "pakwheels_clean.csv"):
            write_csv(batch / name, records, list(records[0]))
        save_json(batch / "manifest.json", {"file_sha256": {name: sha256(batch / name) for name in ("pakwheels_raw.csv", "pakwheels_clean.csv")}})
        assignments = [{"listing_id": "0", "group_id": "listing_0", "partition": "development", "validation_fold": 2},
                       {"listing_id": "1", "group_id": "listing_1", "partition": "demo_test", "validation_fold": None}]
        save_json(parent / "splits.json", {"assignments": assignments})
        save_json(parent / "manifest.json", {"output_sha256": {"splits.json": sha256(parent / "splits.json")}})
        return batch, parent, records

    def test_preparation_roundtrip_preserves_history_and_refuses_overwrite_or_ignored_history(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch, parent, records = self.build_inputs(root)
            args = SimpleNamespace(batch_dir=[batch], parent_evaluation=parent,
                                   output_dir=root / "prepared", report_dir=root / "report",
                                   catalogue=PROJECT_ROOT / "catalogues/cars.json", scope=PROJECT_ROOT / "configs/pilot_scope.json")
            evidence = {row["listing_id"]: {"checks": {}, "updates": {}, "flags": [], "price_verified": True} for row in records}
            original = (batch / "pakwheels_raw.csv").read_bytes()
            with patch("scripts.prepare_modeling_dataset.review_evidence", return_value=evidence):
                manifest = prepare_modeling_dataset(args)
            self.assertEqual(manifest["source_checked_candidates"], 16)
            self.assertEqual((batch / "pakwheels_raw.csv").read_bytes(), original)
            for name, digest in manifest["output_sha256"].items():
                self.assertEqual(sha256(args.output_dir / name), digest)
            with self.assertRaisesRegex(ValueError, "already exists"):
                prepare_modeling_dataset(args)
            parameters = (args.output_dir, root / "evaluation", PROJECT_ROOT / "configs/evaluation_modeling_002.json",
                          args.output_dir / "catalogue.json", args.output_dir / "scope.json")
            prepare_evaluation(*parameters)
            development = load_evaluation_data(args.output_dir, root / "evaluation", "F2")
            self.assertIn("0", development.listing_ids)
            self.assertNotIn("1", development.listing_ids)
            with self.assertRaisesRegex(ValueError, "explicit preservation"):
                prepare_evaluation(args.output_dir, root / "bad_eval", PROJECT_ROOT / "configs/evaluation_pilot.json",
                                   args.output_dir / "catalogue.json", args.output_dir / "scope.json")
            (parent / "manifest.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "Historical evaluation manifest"):
                prepare_evaluation(args.output_dir, root / "tampered", *parameters[2:])


if __name__ == "__main__":
    unittest.main()
