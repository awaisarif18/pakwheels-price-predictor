"""Test collection budgets and recovery with synthetic pages and no network."""

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

import scraper
from collector.runner import CollectionSettings, run_collection
from collector.sampling import SearchSpec, load_plan


def ad_url(number, model="corolla"):
    return f"{scraper.BASE_URL}/used-cars/toyota-{model}-2013-for-sale-in-lahore-{number}"


def ad_html(url, make="Toyota", model="Corolla", complete=True):
    product = {"@type": "Product", "brand": {"name": make}, "model": model, "offers": {"url": url}}
    mileage = "199,128 km" if complete else "Mileage unavailable"
    return (
        f'<html><body><h1>{make} {model} GLi 2013</h1><div>PKR 33.5 lacs | {mileage} | Petrol | Automatic</div>'
        f'<script type="application/ld+json">{json.dumps(product)}</script></body></html>'
    )


def search_html(*urls):
    return "".join(f'<a href="{url}">Car</a>' for url in urls)


def spec(name="corolla", make="Toyota", model="Corolla", target=2, budget=3, pages=2):
    return SearchSpec(name, f"{scraper.BASE_URL}/used-cars/{name}/1?page={{page}}", make, model, target, budget, pages)


class CollectionRunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.output = Path(self.directory.name) / "batch"
        # A missing fetch mock must fail, never make an accidental live request.
        guard = patch("requests.sessions.Session.request", side_effect=AssertionError("Network disabled in offline tests"))
        guard.start()
        self.addCleanup(guard.stop)

    def run_batch(self, specs, pages, budget=10, refresh=False):
        settings = CollectionSettings(tuple(specs), self.output, budget, delay=5, refresh=refresh)
        requested = []

        def fetch(_session, url, _delay):
            requested.append(url)
            value = pages[url]
            if isinstance(value, BaseException):
                raise value
            return value

        with contextlib.redirect_stdout(io.StringIO()), patch.object(scraper, "fetch_page", side_effect=fetch):
            run = run_collection(settings, scraper)
        return run, requested

    def manifest(self):
        return json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))

    def test_round_robin_quotas_and_saved_review_evidence(self):
        first, second = spec(), spec("city", "Honda", "City")
        urls = [ad_url(number) for number in range(1, 5)]
        pages = {
            first.url_template.format(page=1): search_html(*urls[:2]),
            second.url_template.format(page=1): search_html(*urls[2:]),
            **{url: ad_html(url, "Toyota" if index < 2 else "Honda", "Corolla" if index < 2 else "City") for index, url in enumerate(urls)},
        }
        run, requested = self.run_batch([first, second], pages)
        self.assertEqual([url for url in requested if "for-sale" in url], [urls[0], urls[2], urls[1], urls[3]])
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["request_counts"], {"search": 2, "detail": 4})
        self.assertEqual(self.manifest()["group_complete_counts"], {"corolla": 2, "city": 2})
        for event in run["selections"]:
            evidence = self.output / event["html_evidence"]
            self.assertEqual(hashlib.sha256(evidence.read_bytes()).hexdigest(), event["html_sha256"])
        self.assertFalse(list(self.output.glob("*.tmp")))

    def test_resume_skips_and_duplicate_ids_do_not_consume_detail_budget(self):
        group = spec()
        old, alias, new = ad_url(1), ad_url(1, "changed-slug"), ad_url(2)
        row, _ = scraper.parse_car(ad_html(old), old)
        scraper.save_csv({old: row}, self.output)
        run, requested = self.run_batch([group], {
            group.url_template.format(page=1): search_html(old, alias, new), new: ad_html(new),
        }, budget=1)
        self.assertEqual(run["request_counts"]["detail"], 1)
        self.assertEqual(run["selection_outcomes"], {"already_complete": 1, "duplicate": 1, "new_complete": 1})
        self.assertNotIn(old, requested)
        self.assertEqual(self.manifest()["unique_listing_ids"], 2)
        self.assertEqual(run["status"], "completed")

    def test_family_mismatch_and_incomplete_rows_are_retained_without_filling_quota(self):
        group = spec(target=1, budget=3)
        wrong, incomplete, correct = [ad_url(number) for number in [1, 2, 3]]
        run, _ = self.run_batch([group], {
            group.url_template.format(page=1): search_html(wrong, incomplete, correct),
            wrong: ad_html(wrong, "Honda", "City"), incomplete: ad_html(incomplete, complete=False), correct: ad_html(correct),
        })
        manifest = self.manifest()
        self.assertEqual((manifest["total_rows"], manifest["complete_rows"]), (3, 2))
        self.assertEqual(manifest["group_complete_counts"], {"corolla": 1})
        self.assertEqual(manifest["group_assignments"][wrong], "unmatched")
        self.assertEqual(run["selection_outcomes"], {"new_complete": 2, "new_incomplete": 1})
        self.assertTrue((self.output / "evidence" / f"{run['run_id']}_2.txt").exists())

    def test_access_restriction_stops_all_collection_and_preserves_progress(self):
        group = spec(target=3)
        first, restricted, third = [ad_url(number) for number in [1, 2, 3]]
        run, requested = self.run_batch([group], {
            group.url_template.format(page=1): search_html(first, restricted, third),
            first: ad_html(first), restricted: scraper.AccessRestricted("HTTP 429"),
        })
        self.assertEqual(run["status"], "restricted")
        self.assertEqual(run["request_outcomes"], {"success": 2, "restricted": 1})
        self.assertEqual(self.manifest()["total_rows"], 1)
        self.assertNotIn(third, requested)

    def test_operator_interrupt_records_pending_request_and_saves_csv(self):
        group = spec()
        first, second = ad_url(1), ad_url(2)
        run, _ = self.run_batch([group], {
            group.url_template.format(page=1): search_html(first, second),
            first: ad_html(first), second: KeyboardInterrupt(),
        })
        self.assertEqual(run["status"], "interrupted")
        self.assertEqual(run["request_outcomes"]["interrupted"], 1)
        self.assertEqual(len(scraper.load_existing(self.output)), 1)
        self.assertIn("interrupted", (self.output / "collection_summary.md").read_text(encoding="utf-8"))

    def test_failed_detail_request_consumes_budget_and_reports_shortfall(self):
        group = spec()
        first, second, third = [ad_url(number) for number in [1, 2, 3]]
        run, requested = self.run_batch([group], {
            group.url_template.format(page=1): search_html(first, second, third),
            first: requests.ConnectionError("Synthetic connection error"), second: ad_html(second),
        }, budget=2)
        self.assertEqual(run["status"], "partial")
        self.assertEqual(run["request_counts"]["detail"], 2)
        self.assertEqual(run["request_outcomes"]["failed"], 1)
        self.assertEqual(run["groups"]["corolla"]["end_reason"], "run_detail_budget_reached")
        self.assertNotIn(third, requested)

    def test_empty_search_reports_zero_rows_without_error(self):
        group = spec()
        run, _ = self.run_batch([group], {group.url_template.format(page=1): "<html>No results</html>"})
        self.assertEqual(run["status"], "partial")
        self.assertEqual(self.manifest()["total_rows"], 0)
        self.assertEqual(run["groups"]["corolla"]["end_reason"], "no_listing_links")
        self.assertTrue(list((self.output / "diagnostics").glob("*.html")))

    def test_completed_plan_resumes_without_fetching_again_and_rejects_changed_scope(self):
        group = spec(target=1)
        url = ad_url(1)
        self.run_batch([group], {group.url_template.format(page=1): search_html(url), url: ad_html(url)})
        run, requested = self.run_batch([group], {})
        self.assertEqual(requested, [])
        self.assertEqual(run["status"], "completed")
        fingerprint = hashlib.sha256((self.output / "pakwheels_raw.csv").read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "different sampling plan"):
            self.run_batch([spec("city", "Honda", "City")], {})
        self.assertEqual(hashlib.sha256((self.output / "pakwheels_raw.csv").read_bytes()).hexdigest(), fingerprint)


class SamplingPlanTests(unittest.TestCase):
    def test_checked_in_plan_has_180_row_target_and_250_detail_budget(self):
        specs = load_plan(scraper.PROJECT_DIR / "configs" / "collection_pilot.json")
        self.assertEqual(sum(item.target_complete_rows for item in specs), 180)
        self.assertEqual(sum(item.max_detail_requests for item in specs), 250)
        self.assertEqual(len(specs), 5)

    def test_invalid_sources_and_budgets_fail_before_collection(self):
        valid = {
            "name": "corolla", "url_template": scraper.SEARCH_URL,
            "expected_make": "Toyota", "expected_model": "Corolla",
            "target_complete_rows": 2, "max_detail_requests": 3, "max_pages": 1,
        }
        changes = [
            {"url_template": "https://example.com/used-cars/?page={page}"},
            {"url_template": "https://www.pakwheels.com/used-cars/?page={wrong}"},
            {"max_detail_requests": 0}, {"target_complete_rows": True},
            {"expected_model": None}, {"max_pages": -1},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            for change in changes:
                with self.subTest(change=change):
                    path.write_text(json.dumps({"plan_version": 1, "searches": [{**valid, **change}]}), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        load_plan(path)


if __name__ == "__main__":
    unittest.main()
