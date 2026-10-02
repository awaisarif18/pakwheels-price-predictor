"""Check conservative identity, source corrections, and candidate selection."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from pilot.evidence import review_evidence
from pilot.identity import load_catalogue, resolve_identity
from pilot.paths import PROJECT_ROOT
from pilot.profile import coverage
from pilot.quality import prepare_rows


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = load_catalogue(PROJECT_ROOT / "catalogues/cars.json")
        self.scope = json.loads((PROJECT_ROOT / "configs/pilot_scope.json").read_text(encoding="utf-8"))

    def row(self, **changes):
        row = {
            "listing_id": "1", "car_title": "Toyota Corolla GLi 1.3 VVTi 2013",
            "make": "Toyota", "model": "Corolla", "variant": "GLi 1.3 VVTi",
            "year": "2013", "price_pkr": "3350000.0", "mileage_km": "0",
            "engine_cc": "1300.0", "fuel": "Cng", "transmission": "Manual",
            "listing_city": "Lahore", "assembly": "Local", "body_type": "N/A",
            "registration_year": "2015.0", "registration_year_meaning": "unknown",
            "parse_status": "complete", "source_url": "https://www.pakwheels.com/used-cars/toyota-corolla-2013-for-sale-in-lahore-1",
        }
        row.update(changes)
        return row

    def test_normalization_preserves_zero_unknown_registration_and_originals(self):
        original = self.row(variant="")
        snapshot = copy.deepcopy(original)
        rows = prepare_rows((original,), self.catalogue, self.scope, {})
        row = rows[0]
        self.assertEqual(original, snapshot)
        self.assertEqual(row["mileage_km"], 0)
        self.assertEqual(row["fuel"], "CNG")
        self.assertIsNone(row["body_type"])
        self.assertIsNone(row["variant"])
        self.assertTrue(row["modeling_candidate"])
        self.assertFalse(row["source_checked_candidate"])
        self.assertNotIn("registration_gap", row)
        self.assertIn("registration_meaning_unknown", row["quality_notes"])
        self.assertEqual(coverage(rows, "family")[0]["missing_mileage_km"], 0)

    def test_unknown_variants_are_not_merged_into_a_similar_known_variant(self):
        row = self.row(make="Honda", model="Civic", variant="Oriel mystery edition")
        identity = resolve_identity(row, self.catalogue)
        self.assertEqual(identity["variant"], "Oriel mystery edition")
        self.assertEqual(identity["identity_status"], "unresolved_variant")
        prepared = prepare_rows((row,), self.catalogue, self.scope, {})[0]
        self.assertFalse(prepared["modeling_candidate"])
        for variant in ["Oriel", "Oriel 1.8 i-VTEC CVT"]:
            self.assertEqual(resolve_identity({**row, "variant": variant}, self.catalogue)["variant"], variant)

    def test_source_updates_apply_to_derived_copy_and_year_scope_is_explicit(self):
        original = self.row(price_pkr="3095000")
        evidence = {"1": {"updates": {"price_pkr": 4850000}, "price_verified": True, "flags": []}}
        row = prepare_rows((original,), self.catalogue, self.scope, evidence)[0]
        self.assertEqual(row["price_pkr"], 4850000)
        self.assertEqual(original["price_pkr"], "3095000")
        self.assertTrue(row["source_checked_candidate"])
        old = prepare_rows((self.row(year="2005"),), self.catalogue, self.scope, {})[0]
        self.assertFalse(old["modeling_candidate"])
        self.assertIn("outside_candidate_year_range", old["exclusion_reasons"])

    def test_possible_reposts_share_split_group_without_deleting_rows_or_using_price(self):
        rows = prepare_rows((self.row(), self.row(listing_id="2", price_pkr="4000000")), self.catalogue, self.scope, {})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["group_id"], rows[1]["group_id"])
        self.assertTrue(rows[0]["group_id"].startswith("suspected_"))

    def test_cached_evidence_correction_requires_matching_product_and_agreeing_price_box(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = Path(directory)
            (batch / "runs").mkdir()
            row = self.row(price_pkr="3095000")
            product = {"offers": {"url": row["source_url"], "price": 4850000}, "modelDate": 2013, "mileageFromOdometer": "0 km", "fuelType": "CNG", "vehicleTransmission": "Manual"}
            html = f'<html><h1>{row["car_title"]}</h1><div class="price-box"><strong>PKR 48.5 lacs</strong></div><script type="application/ld+json">{json.dumps(product)}</script></html>'
            path = batch / "source.html"
            path.write_text(html, encoding="utf-8")
            event = {"url": row["source_url"], "html_evidence": "source.html", "html_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            (batch / "runs/run.json").write_text(json.dumps({"selections": [event]}), encoding="utf-8")
            review = review_evidence(batch, (row,))["1"]
            self.assertTrue(review["price_verified"])
            self.assertEqual(review["updates"], {"price_pkr": 4850000})
            path.write_text(html + "modified", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                review_evidence(batch, (row,))


if __name__ == "__main__":
    unittest.main()
