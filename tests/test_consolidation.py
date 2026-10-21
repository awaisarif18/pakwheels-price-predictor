"""Protect observation selection, historical links, and reserved-test isolation."""

import copy
import unittest

from pilot.consolidate import consolidate_observations
from pilot.continued_splits import build_continued_splits
from scripts.prepare_modeling_dataset import expand_catalogue


def row(number="1", **changes):
    return {"listing_id": number, "make": "Honda", "model": "City", "variant": "1.3",
            "year": 2020, "mileage_km": 1000, "engine_cc": 1300, "fuel": "Petrol", "transmission": "Manual",
            "listing_city": "Lahore", "assembly": "Local", "price_pkr": 1000000,
            "collected_at": "2026-10-01T00:00:00+00:00", "source_batch": "old",
            "source_checked_candidate": True, "modeling_candidate": True, "exclusion_reasons": "", **changes}


class ConsolidationTests(unittest.TestCase):
    def test_latest_observation_does_not_fall_back_to_older_checked_price(self):
        old = row()
        latest = row(collected_at="2026-10-17T00:00:00+00:00", source_batch="new",
                     price_pkr=900000, source_checked_candidate=False)
        originals = copy.deepcopy([old, latest])
        result, decisions = consolidate_observations([latest, old], [])
        self.assertEqual(result[0]["price_pkr"], 900000)
        self.assertFalse(result[0]["source_checked_candidate"])
        self.assertEqual(result[0]["observation_count"], 2)
        self.assertEqual([old, latest], originals)
        again, _ = consolidate_observations([old, latest], [])
        self.assertEqual(result, again)

    def test_old_spec_link_survives_mileage_change_and_quarantines_test_conflict(self):
        observations = [row(), row("2", price_pkr=1500000),
                        row(collected_at="2026-10-17T00:00:00+00:00", mileage_km=2000, source_batch="new")]
        history = [
            {"listing_id": "1", "group_id": "old1", "partition": "demo_test", "validation_fold": None},
            {"listing_id": "2", "group_id": "old2", "partition": "development", "validation_fold": 1},
        ]
        result, _ = consolidate_observations(observations, history)
        self.assertEqual(result[0]["group_id"], result[1]["group_id"])
        self.assertTrue(all(item["historical_partition"] == "quarantined" for item in result))
        self.assertTrue(all(not item["source_checked_candidate"] for item in result))

    def test_reserved_vehicle_and_matching_new_id_remain_reserved_without_deletion(self):
        history = [{"listing_id": "1", "group_id": "old", "partition": "demo_test", "validation_fold": None}]
        result, _ = consolidate_observations([row(), row("2", price_pkr=2000000)], history)
        self.assertEqual(len(result), 2)
        self.assertTrue(all(item["historical_partition"] == "demo_test" for item in result))

    def test_family_conflict_and_ambiguous_latest_timestamp_reject_eligibility(self):
        result, _ = consolidate_observations([row(), row(make="Toyota", model="Corolla", source_batch="new",
                                                        collected_at="2026-10-17T00:00:00+00:00")], [])
        self.assertIn("cross_batch_family_conflict", result[0]["exclusion_reasons"])
        with self.assertRaisesRegex(ValueError, "timestamp"):
            consolidate_observations([row(), row(source_batch="other", price_pkr=1234567)], [])

    def test_catalogue_addition_requires_exact_cached_heading_and_unique_product(self):
        from pathlib import Path
        catalogue = {"catalogue_version": 1, "families": [{"make": "Honda", "model": "City", "variants": []}]}
        original = copy.deepcopy(catalogue)
        member = {"listing_id": "1", "make": "Honda", "model": "City", "variant": "Special", "year": "2020"}
        evidence = {"1": {"matched_product_count": 1, "source_title": "Honda City Special 2020", "html_path": "a.html", "html_sha256": "abc"}}
        expanded, additions = expand_catalogue(catalogue, [(Path("batch"), [member], evidence)])
        self.assertEqual(catalogue, original)
        self.assertEqual(expanded["families"][0]["variants"], ["Special"])
        self.assertEqual(len(additions), 1)
        for title in (None, "Honda City Other 2020"):
            evidence["1"]["source_title"] = title
            self.assertEqual(expand_catalogue(catalogue, [(Path("batch"), [member], evidence)])[1], [])

    def test_continued_splits_never_move_old_development_to_test(self):
        observations = [row(str(index), mileage_km=index * 1000) for index in range(12)]
        history = [
            {"listing_id": "0", "group_id": "old0", "partition": "development", "validation_fold": 2},
            {"listing_id": "1", "group_id": "old1", "partition": "demo_test", "validation_fold": None},
        ]
        prepared, _ = consolidate_observations(observations, history)
        config = {"seed": 42, "test_fraction": 0.2, "development_folds": 3}
        split = build_continued_splits(prepared, config)
        assignments = {item["listing_id"]: item for item in split["assignments"]}
        self.assertEqual(assignments["0"]["partition"], "development")
        self.assertEqual(assignments["0"]["validation_fold"], 2)
        self.assertEqual(assignments["1"]["partition"], "demo_test")
        self.assertEqual(split, build_continued_splits(list(reversed(prepared)), config))

    def test_reviewed_rebuild_keeps_holdout_and_existing_folds_with_one_reinstatement(self):
        observations = [row(str(index), mileage_km=index * 1000) for index in range(7)]
        history = [{"listing_id": str(index), "group_id": f"listing_{index}",
                    "partition": "demo_test" if index == 0 else "development",
                    "validation_fold": None if index == 0 else (index - 1) % 3} for index in range(6)]
        prepared, _ = consolidate_observations(observations, history)
        config = {"seed": 42, "test_fraction": 0.2, "development_folds": 3, "new_group_policy": "development_only"}
        rebuilt = build_continued_splits(prepared, config)
        assignments = {item["listing_id"]: item for item in rebuilt["assignments"]}
        for previous in history:
            self.assertEqual(assignments[previous["listing_id"]]["partition"], previous["partition"])
            self.assertEqual(assignments[previous["listing_id"]]["validation_fold"], previous["validation_fold"])
        self.assertEqual(assignments["6"]["partition"], "development")
        changed = [{**item, "price_pkr": 999999999} for item in reversed(prepared)]
        self.assertEqual(rebuilt, build_continued_splits(changed, config))
        without_new = [item for item in prepared if item["listing_id"] != "6"]
        self.assertEqual(len(build_continued_splits(without_new, config)["assignments"]), 6)

    def test_reviewed_rebuild_exclusions_do_not_reallocate_surviving_history(self):
        observations = [row(str(index), mileage_km=index * 1000) for index in range(8)]
        history = [{"listing_id": str(index), "group_id": f"listing_{index}",
                    "partition": "demo_test" if index == 0 else "development",
                    "validation_fold": None if index == 0 else (index - 1) % 3} for index in range(8)]
        prepared, _ = consolidate_observations(observations, history)
        remaining = [item for item in prepared if item["listing_id"] not in {"4", "5"}]
        config = {"seed": 42, "test_fraction": 0.2, "development_folds": 3, "new_group_policy": "development_only"}
        splits = build_continued_splits(remaining, config)
        self.assertEqual({item["listing_id"] for item in splits["assignments"]}, {"0", "1", "2", "3", "6", "7"})
        self.assertEqual([item["listing_id"] for item in splits["assignments"] if item["partition"] == "demo_test"], ["0"])


if __name__ == "__main__":
    unittest.main()
