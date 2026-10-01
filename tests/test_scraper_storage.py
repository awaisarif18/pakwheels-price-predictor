"""Verify collector storage behavior after organizing its output paths."""

import tempfile
import unittest
import contextlib
import io
from pathlib import Path
from unittest.mock import patch

import scraper
import pandas as pd


class ScraperStorageTests(unittest.TestCase):
    def test_export_resume_and_diagnostics_create_nested_directories(self) -> None:
        html = (
            "<html><body><h1>Honda City 2022</h1>"
            "<div>PKR 43 lacs | 0 km | Petrol | Automatic | 1200 cc</div>"
            "</body></html>"
        )
        url = scraper.BASE_URL + "/used-cars/honda-city-for-sale-in-lahore-123"
        row, preview = scraper.parse_car(html, url)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            current = workspace / "data" / "raw" / "current"
            debug = workspace / "data" / "debug_pages"
            with patch.multiple(
                scraper,
                DATA_DIR=current,
                RAW_FILE=current / "pakwheels_raw.csv",
                CLEAN_FILE=current / "pakwheels_clean.csv",
                DEBUG_DIR=debug,
            ):
                self.assertEqual(scraper.save_csv({url: row}), (1, 1))
                loaded = scraper.load_existing()
                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[url]["mileage_km"], 0)
                scraper.save_debug(html, url, row, preview)
                self.assertEqual((debug / "failed_123.html").read_text(encoding="utf-8"), html)

    def test_separate_batch_resumes_legacy_rows_without_fabricating_new_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "batch"
            output.mkdir()
            url = scraper.BASE_URL + "/used-cars/honda-city-for-sale-in-lahore-123"
            legacy = {"listing_id": "123", "source_url": url, "parse_status": "complete", "year": 2022}
            pd.DataFrame([legacy]).to_csv(output / "pakwheels_raw.csv", index=False)
            records = scraper.load_existing(output)
            self.assertEqual(scraper.save_csv(records, output), (1, 1))
            saved = pd.read_csv(output / "pakwheels_raw.csv")
            self.assertTrue(pd.isna(saved.iloc[0]["assembly"]))
            self.assertTrue(pd.isna(saved.iloc[0]["collection_schema_version"]))
            self.assertEqual(saved.iloc[0]["listing_id"], 123)

    def test_refresh_flag_fetches_saved_row_into_selected_batch(self):
        html = (
            '<html><body><h1>Honda City 2022</h1><div>PKR 43 lacs | 0 km | Petrol | Automatic</div>'
            '<ul id="scroll_car_detail"><li class="ad-data">Assembly</li><li>Local</li></ul></body></html>'
        )
        url = scraper.BASE_URL + "/used-cars/honda-city-for-sale-in-lahore-123"
        row, _ = scraper.parse_car(html, url)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            scraper.save_csv({url: row}, output)
            command = ["scraper.py", "--url", url, "--output-dir", str(output), "--delay", "1"]
            with contextlib.redirect_stdout(io.StringIO()), patch("scraper.fetch_page", return_value=html) as fetch:
                with patch("sys.argv", command):
                    scraper.main()
                fetch.assert_not_called()
                with patch("sys.argv", command + ["--refresh"]):
                    scraper.main()
                fetch.assert_called_once()
            saved = scraper.load_existing(output)[url]
            self.assertEqual(saved["assembly"], "Local")
            self.assertEqual(saved["collection_schema_version"], 2)


if __name__ == "__main__":
    unittest.main()
