"""Prepare versioned pilot copies and quality reports using local evidence only."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from collector.run_log import write_json
from pilot.audit import audit_csv
from pilot.evidence import review_evidence
from pilot.identity import load_catalogue
from pilot.paths import PROJECT_ROOT
from pilot.profile import coverage, render_quality_report
from pilot.quality import prepare_rows


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=PROJECT_ROOT / "data/raw/pilot_batch_001")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/processed/pilot_batch_001_v2")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/pilot_batch_001")
    parser.add_argument("--catalogue", type=Path, default=PROJECT_ROOT / "catalogues/cars.json")
    parser.add_argument("--scope", type=Path, default=PROJECT_ROOT / "configs/pilot_scope.json")
    args = parser.parse_args()
    batch, output = args.batch_dir.resolve(), args.output_dir.resolve()
    if output.exists():
        parser.error("Processed dataset already exists; choose a new --output-dir to preserve versions")
    if output == batch or output.is_relative_to(PROJECT_ROOT / "data/raw") or batch.is_relative_to(output):
        parser.error("Processed output must be separate from raw data")
    raw = audit_csv(batch / "pakwheels_raw.csv")
    clean = audit_csv(batch / "pakwheels_clean.csv")
    complete_raw = Counter(tuple(sorted(row.items())) for row in raw.rows if row["parse_status"] == "complete")
    if raw.issues or clean.issues or raw.duplicate_ids or raw.duplicate_urls or complete_raw != Counter(tuple(sorted(row.items())) for row in clean.rows):
        parser.error("Input integrity checks failed; resolve the audit before preparation")
    catalogue = load_catalogue(args.catalogue)
    scope = json.loads(args.scope.read_text(encoding="utf-8"))
    evidence = review_evidence(batch, raw.rows)
    rows = prepare_rows(raw.rows, catalogue, scope, evidence)
    candidates = [row for row in rows if row["modeling_candidate"]]
    checked = [row for row in rows if row["source_checked_candidate"]]
    fingerprints = {"raw_sha256": raw.sha256, "clean_sha256": clean.sha256, "catalogue_sha256": hashlib.sha256(args.catalogue.read_bytes()).hexdigest(), "scope_sha256": hashlib.sha256(args.scope.read_bytes()).hexdigest()}
    if hashlib.sha256(raw.path.read_bytes()).hexdigest() != raw.sha256 or hashlib.sha256(clean.path.read_bytes()).hexdigest() != clean.sha256:
        parser.error("Raw files changed during preparation; stop collection and retry offline")
    output.mkdir(parents=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    for name, members in [("normalized_all.csv", rows), ("modeling_candidates.csv", candidates), ("source_checked_candidates.csv", checked)]:
        write_csv(output / name, members, fields)
    for dimension in ["family", "year", "listing_city"]:
        data = coverage(rows, dimension)
        write_csv(args.report_dir / f"coverage_by_{dimension}.csv", data, list(data[0]) if data else [])
    write_json(args.report_dir / "evidence_review.json", evidence)
    (args.report_dir / "data_quality.md").write_text(render_quality_report(rows, evidence, fingerprints), encoding="utf-8")
    manifest = {
        "preparation_schema_version": 1, "dataset_id": output.name, "created_at": datetime.now(timezone.utc).isoformat(),
        "input_fingerprints": fingerprints, "scope": scope,
        "rows": len(rows), "modeling_candidates": len(candidates), "source_checked_candidates": len(checked),
        "cached_evidence_rows": len(evidence),
        "source_updates": [{"listing_id": number, "updates": item["updates"], "html_path": item["html_path"], "html_sha256": item["html_sha256"]} for number, item in evidence.items() if item["updates"]],
        "output_sha256": {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in ["normalized_all.csv", "modeling_candidates.csv", "source_checked_candidates.csv"]},
        "code_sha256": {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() for name in ["pilot/evidence.py", "pilot/identity.py", "pilot/quality.py", "pilot/profile.py", "scripts/prepare_dataset.py"]},
        "training_status": "not_run", "source_policy": "cached source agreement, not seller factual correctness",
    }
    write_json(output / "manifest.json", manifest)
    print(f"Prepared {len(rows)} rows; {len(candidates)} modeling candidates; {len(checked)} source-checked candidates.")
    print(f"Data: {output}\nReport: {(args.report_dir / 'data_quality.md').resolve()}")


if __name__ == "__main__":
    main()
