"""Verify collector storage behavior after organizing its output paths."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scraper


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


if __name__ == "__main__":
    unittest.main()
