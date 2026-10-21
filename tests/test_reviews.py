"""Human rejections block later modeling; registration never becomes an input."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pilot.features import FEATURE_SETS
from pilot.reviews import apply_reviews, load_reviews, reject_excluded_population


class ReviewTests(unittest.TestCase):
    def test_explicit_rejection_preserves_raw_copy_and_excludes_related_group(self):
        rows = [{"listing_id": str(i), "group_id": group, "exclusion_reasons": reason,
                 "price_pkr": 300000, "modeling_candidate": not reason, "source_checked_candidate": not reason}
                for i, group, reason in [(1, "same", ""), (2, "same", ""), (3, "other", "outside_candidate_year_range")]]
        decisions = {"1": {"decision": "exclude"}, "3": {"decision": "keep"}}
        prepared = apply_reviews(rows, decisions)
        self.assertTrue(rows[0]["modeling_candidate"])
        self.assertTrue(all(not row["modeling_candidate"] for row in prepared))
        self.assertEqual(prepared[0]["price_pkr"], 300000)
        self.assertIn("manual_review_excluded", prepared[0]["exclusion_reasons"])
        self.assertIn("group_linked_to_manual_review_exclusion", prepared[1]["exclusion_reasons"])
        self.assertEqual(prepared[2]["exclusion_reasons"], "outside_candidate_year_range")

    def test_stale_population_fails_instead_of_silently_changing_fixed_membership(self):
        with patch("pilot.reviews.load_reviews", return_value={"1": {"decision": "exclude"}}):
            with self.assertRaisesRegex(ValueError, "Prepare a new reviewed dataset"):
                reject_excluded_population([{"listing_id": "1"}])
            reject_excluded_population([{"listing_id": "2"}])

    def test_decisions_require_unique_ids_clear_status_and_reasons(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "reviews.json"
            good = {"listing_id": "1", "decision": "exclude", "reason": "User confirmed invalid entry"}
            for decisions in ([good, good], [{**good, "decision": "maybe"}], [{**good, "reason": ""}]):
                path.write_text(json.dumps({"version": 1, "decisions": decisions}))
                with self.assertRaises(ValueError):
                    load_reviews(path)
            path.write_text(json.dumps({"version": 1, "decisions": [good]}))
            self.assertEqual(load_reviews(path)["1"], good)

    def test_registration_and_registration_gap_are_outside_every_model_input_set(self):
        for fields in FEATURE_SETS.values():
            self.assertFalse(any("registration" in field for field in fields))

    def test_mileage_correction_is_explicit_repeatable_and_preserves_original(self):
        row = {"listing_id": "1", "group_id": "listing_1", "mileage_km": 100,
               "exclusion_reasons": "", "modeling_candidate": True, "source_checked_candidate": True}
        decisions = {"1": {"decision": "keep", "corrections": {"mileage_km": {"from": 100, "to": 100000}}}}
        updated = apply_reviews([row], decisions)[0]
        self.assertEqual(row["mileage_km"], 100)
        self.assertEqual(updated["mileage_km"], 100000)
        self.assertEqual(json.loads(updated["manual_updates"])["mileage_km"]["from"], 100)
        self.assertEqual(apply_reviews([updated], decisions)[0], updated)
        with self.assertRaises(ValueError):
            apply_reviews([{**row, "mileage_km": 999}], decisions)
        with patch("pilot.reviews.load_reviews", return_value=decisions):
            with self.assertRaisesRegex(ValueError, "predates a manual correction"):
                reject_excluded_population([row])
            reject_excluded_population([updated])

    def test_price_acceptance_requires_the_exact_pair_and_does_not_invent_source_agreement(self):
        row = {"listing_id": "1", "group_id": "listing_1", "source_batch": "batch", "price_pkr": 2800000,
               "source_price_verified": False, "exclusion_reasons": "unresolved_source_disagreement",
               "modeling_candidate": False, "source_checked_candidate": False}
        decisions = {"1": {"decision": "keep", "accept_price_precision": {"displayed_pkr": 2800000, "structured_pkr": 2799999}}}
        evidence = {"batch": {"1": {"price_box_value": 2800000, "checks": {"price_pkr": {"source": 2799999}},
                                     "flags": ["unresolved_source_disagreement:price_pkr"]}}}
        updated = apply_reviews([row], decisions, evidence)[0]
        self.assertTrue(updated["source_checked_candidate"])
        self.assertTrue(updated["manual_price_accepted"])
        self.assertFalse(updated["source_price_verified"])
        with self.assertRaises(ValueError):
            apply_reviews([row], decisions)
        with self.assertRaises(ValueError):
            apply_reviews([{**row, "price_pkr": 2800100}], decisions, evidence)
        scoped = apply_reviews([{**row, "exclusion_reasons": "unresolved_source_disagreement;outside_candidate_year_range"}], decisions, evidence)[0]
        self.assertFalse(scoped["modeling_candidate"])


if __name__ == "__main__":
    unittest.main()
