"""Validate new fields on baseline URLs in a separate, reproducible batch.

Offline by default. --fetch-missing permits sequential downloads for evidence
that is not already cached. Existing HTML is reused and never re-fetched here.
"""

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone

import requests

import scraper
from pilot.paths import BASELINE_DIR, PROJECT_ROOT

BATCH_ID = "field_validation_2026-10-01"
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / BATCH_ID


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-missing", action="store_true")
    parser.add_argument("--delay", type=float, default=5)
    args = parser.parse_args()
    if args.delay < 1:
        parser.error("--delay must be at least one second")

    started = datetime.now(timezone.utc).isoformat()
    clock_start = time.monotonic()
    baseline_file = BASELINE_DIR / "pakwheels_raw.csv"
    with baseline_file.open(encoding="utf-8-sig", newline="") as handle:
        baseline = list(csv.DictReader(handle))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scraper.DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    manifest_file = OUTPUT_DIR / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {"batch_id": BATCH_ID, "runs": []}
    run = {"started_at": started, "fetch_missing": args.fetch_missing, "requests": [], "cache_reused": 0}
    run["code_sha256"] = {
        name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
        for name in ["scraper.py", "collector/fields.py", "scripts/validate_collection.py"]
    }
    manifest["runs"].append(run)
    records, evidence = {}, []
    with requests.Session() as session:
        session.headers["User-Agent"] = "CarPriceResearch/0.2"
        for original in baseline:
            listing_id, url = original["listing_id"], original["source_url"]
            if not listing_id.isascii() or not listing_id.isdigit():
                raise ValueError("Baseline listing ID is invalid")
            if url not in scraper.listing_links(f'<a href="{url}"></a>'):
                raise ValueError("Baseline URL is not a permitted PakWheels listing")
            path = scraper.DEBUG_DIR / f"field_mapping_{listing_id}.html"
            if path.exists():
                run["cache_reused"] += 1
            elif args.fetch_missing:
                event = {"listing_id": listing_id, "url": url, "started_at": datetime.now(timezone.utc).isoformat()}
                run["requests"].append(event)
                try:
                    html = scraper.fetch_page(session, url, args.delay)
                except (scraper.AccessRestricted, requests.RequestException) as exc:
                    event.update(outcome="stopped", error=str(exc))
                    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                    print(f"[STOP] {exc}", flush=True)
                    break
                event["outcome"] = "success"
                path.write_text(html, encoding="utf-8")
                event["completed_at"] = datetime.now(timezone.utc).isoformat()
                manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            else:
                print(f"[MISSING EVIDENCE] {listing_id}; use --fetch-missing to download", flush=True)
                continue
            html = path.read_text(encoding="utf-8")
            row, _ = scraper.parse_car(html, url)
            # The filesystem timestamp records cache creation, not this offline parse.
            row["collected_at"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
            records[url] = row
            evidence.append({"listing_id": listing_id, "html_path": str(path.relative_to(PROJECT_ROOT)), "html_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "collected_at_basis": "cache_file_mtime"})
            print(json.dumps({key: row[key] for key in ["listing_id", "make", "model", "variant", "assembly", "body_type", "registration_year", "registration_year_meaning", "listing_date", "listing_date_type"]}), flush=True)

    raw_count, clean_count = scraper.save_csv(records, OUTPUT_DIR)
    run.update(finished_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic() - clock_start, 3))
    availability = {field: sum(row.get(field) is not None for row in records.values()) for field in ["make", "model", "variant", "assembly", "body_type", "registration_year", "listing_date"]}
    manifest.update(schema_version=2, baseline_sha256=hashlib.sha256(baseline_file.read_bytes()).hexdigest(), requested_urls=len(baseline), parsed_rows=raw_count, complete_rows=clean_count, field_non_null_counts=availability, evidence=evidence)
    logged_ids = {
        event["listing_id"] for recorded_run in manifest["runs"]
        for event in recorded_run["requests"] if event.get("outcome") == "success"
    }
    manifest["cached_evidence_without_request_event"] = [item["listing_id"] for item in evidence if item["listing_id"] not in logged_ids]
    manifest["raw_sha256"] = hashlib.sha256((OUTPUT_DIR / "pakwheels_raw.csv").read_bytes()).hexdigest()
    manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    lines = ["# New-field validation sample", "", f"Batch: `{BATCH_ID}`. Parsed {raw_count}/{len(baseline)} baseline URLs; {clean_count} parser-complete rows.", "", "The sample tests extraction and availability. It is not additional independent training data.", "", "| Field | Non-null rows |", "|---|---:|"]
    lines.extend(f"| {field} | {count}/{raw_count} |" for field, count in availability.items())
    lines.extend(["", f"Listing date meanings: `{dict(Counter(row['listing_date_type'] for row in records.values()))}`.", f"Registration meanings: `{dict(Counter(row['registration_year_meaning'] for row in records.values()))}`.", "", "Identity names are source-normalized; catalogue review is still pending. Dates labeled Last Updated are updates, not original posting dates. Registration fields remain optional and only explicit statements are extracted.", "", "The manifest records per-run requests, reused files, HTML checksums, and the baseline checksum. Evidence cached before the first manifest run has no request timing record; its collection timestamp uses filesystem metadata.", ""])
    (OUTPUT_DIR / "validation_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[DONE] {OUTPUT_DIR}: {clean_count}/{raw_count} complete; {availability}")


if __name__ == "__main__":
    main()
