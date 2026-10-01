"""Behavioral checks for evidence preservation and local audit failure cases."""

import csv
import tempfile
import unittest
from pathlib import Path

from pilot.audit import REQUIRED_COLUMNS, audit_csv, render_report, seed_identity_review


class AuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def write_dataset(self, name: str, rows: list[dict[str, str]]) -> Path:
        path = self.directory / name
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=sorted(REQUIRED_COLUMNS))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def record(self, **changes: str) -> dict[str, str]:
        row = {field: "" for field in REQUIRED_COLUMNS}
        row.update({
            "listing_id": "123", "car_title": "Example EV 2022", "year": "2022",
            "price_pkr": "4300000", "mileage_km": "0", "fuel": "Electric",
            "source_url": "https://www.pakwheels.com/used-cars/example-for-sale-in-lahore-123",
            "collected_at": "2026-10-01T08:00:00+00:00", "parse_status": "complete",
        })
        row.update(changes)
        return row

    def test_zero_mileage_and_missing_ev_engine_preserve_input(self) -> None:
        path = self.write_dataset("raw.csv", [self.record()])
        original = path.read_bytes()
        audit = audit_csv(path)
        self.assertEqual(audit.issues, ())
        self.assertEqual(audit.missing_fields["engine_cc"], 1)
        self.assertEqual(audit.complete_count, 1)
        self.assertEqual(path.read_bytes(), original)

    def test_duplicate_and_invalid_values_are_reported(self) -> None:
        path = self.write_dataset("raw.csv", [
            self.record(), self.record(price_pkr="NaN", mileage_km="-1", year=""),
        ])
        audit = audit_csv(path)
        self.assertEqual(audit.duplicate_ids, {"123": 2})
        flagged_fields = {issue.field for issue in audit.issues}
        self.assertTrue({"price_pkr", "mileage_km", "year"}.issubset(flagged_fields))

    def test_missing_columns_and_malformed_rows_fail(self) -> None:
        path = self.directory / "bad.csv"
        path.write_text("listing_id\n123\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing columns"):
            audit_csv(path)
        path.write_text(
            ",".join(sorted(REQUIRED_COLUMNS)) + "\n123,only-two-values\n", encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "malformed CSV"):
            audit_csv(path)

    def test_existing_manual_review_is_never_overwritten(self) -> None:
        audit = audit_csv(self.write_dataset("raw.csv", [self.record()]))
        review_path = self.directory / "review.csv"
        self.assertTrue(seed_identity_review(audit, review_path))
        review_path.write_text("manual review already entered\n", encoding="utf-8")
        original = review_path.read_bytes()
        self.assertFalse(seed_identity_review(audit, review_path))
        self.assertEqual(review_path.read_bytes(), original)

    def test_clean_export_mismatch_is_not_reported_as_clean(self) -> None:
        raw = audit_csv(self.write_dataset("raw.csv", [self.record()]))
        clean = audit_csv(self.write_dataset("clean.csv", []))
        report = render_report(raw, clean, "fixed-test-time")
        self.assertIn("No; investigate", report)
        self.assertIn("Clean export differs", report)
        self.assertNotIn("No flags from", report)


if __name__ == "__main__":
    unittest.main()
