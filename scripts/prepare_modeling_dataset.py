"""Audit and consolidate saved batches with a new observed-label catalogue."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from pilot.audit import audit_csv
from pilot.consolidate import consolidate_observations
from pilot.evaluate import sha256
from pilot.evidence import review_evidence
from pilot.identity import label, load_catalogue, resolve_identity
from pilot.paths import PROJECT_ROOT
from pilot.profile import coverage, render_quality_report
from pilot.quality import prepare_rows
from pilot.reviews import REVIEW_PATH, apply_reviews, load_reviews
from scripts.prepare_dataset import write_csv
from scripts.prepare_evaluation import save_json


def audit_batch(batch):
    raw, clean = (audit_csv(batch / name) for name in ("pakwheels_raw.csv", "pakwheels_clean.csv"))
    complete = Counter(tuple(sorted(row.items())) for row in raw.rows if row["parse_status"] == "complete")
    if (raw.issues or clean.issues or raw.duplicate_ids or raw.duplicate_urls or
            complete != Counter(tuple(sorted(row.items())) for row in clean.rows)):
        raise ValueError(f"Batch integrity checks failed: {batch.name}")
    manifest = json.loads((batch / "manifest.json").read_text(encoding="utf-8"))
    for export, fingerprint in manifest["file_sha256"].items():
        if sha256(batch / export) != fingerprint:
            raise ValueError(f"Batch export differs from collection manifest: {batch.name}/{export}")
    return raw.rows


def expand_catalogue(catalogue, batches):
    """Accept only exact source-heading labels; never invent aliases or trims."""
    result = json.loads(json.dumps(catalogue))
    additions = []
    for batch, rows, evidence in batches:
        for row in rows:
            identity = resolve_identity(row, result)
            if identity["identity_status"] != "unresolved_variant":
                continue
            review = evidence.get(row["listing_id"], {})
            expected = " ".join(str(row[field]) for field in ("make", "model", "variant", "year"))
            if (review.get("matched_product_count") != 1 or
                    (label(review.get("source_title")) or "").casefold() != label(expected).casefold()):
                continue
            family = next(item for item in result["families"] if
                          (item["make"], item["model"]) == (identity["make"], identity["model"]))
            family["variants"].append(identity["variant"])
            additions.append({"make": family["make"], "model": family["model"], "variant": identity["variant"],
                              "source_batch": batch.name, "listing_id": row["listing_id"],
                              "html_path": review["html_path"], "html_sha256": review["html_sha256"]})
    result["revision"] = "modeling_002_observed_labels_v1"
    return result, additions


def input_hashes(batches, catalogue, scope, parent):
    files = [catalogue, scope] + [path for path in parent.iterdir() if path.is_file()]
    for batch in batches:
        files.extend(batch / name for name in ("pakwheels_raw.csv", "pakwheels_clean.csv", "manifest.json"))
        files.extend((batch / "runs").glob("*.json"))
    return {str(path.resolve()): sha256(path) for path in files}


def verify_parent(parent):
    manifest = json.loads((parent / "manifest.json").read_text(encoding="utf-8"))
    for name, fingerprint in manifest["output_sha256"].items():
        if sha256(parent / name) != fingerprint:
            raise ValueError("Historical evaluation artifact changed")
    return json.loads((parent / "splits.json").read_text(encoding="utf-8"))["assignments"]


def save_dataset(output, report, observations, rows, decisions, catalogue, additions, batches, fingerprints, args):
    candidates = [row for row in rows if row["modeling_candidate"]]
    checked = [row for row in rows if row["source_checked_candidate"]]
    output.mkdir(parents=True)
    for name, members in (("observations.csv", observations), ("normalized_all.csv", rows),
                          ("modeling_candidates.csv", candidates), ("source_checked_candidates.csv", checked)):
        write_csv(output / name, members, list(members[0]) if members else list(rows[0]))
    save_json(output / "catalogue.json", catalogue)
    (output / "scope.json").write_bytes(args.scope.read_bytes())
    (output / "manual_reviews.json").write_bytes(REVIEW_PATH.read_bytes())
    write_csv(report / "consolidation.csv", decisions, list(decisions[0]))
    save_json(report / "catalogue_additions.json", additions)
    for dimension in ("family", "year", "listing_city"):
        values = coverage(rows, dimension)
        write_csv(report / f"coverage_by_{dimension}.csv", values, list(values[0]))
    manifest = {
        "preparation_schema_version": 1, "dataset_id": output.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_fingerprints": {"catalogue_sha256": sha256(output / "catalogue.json"), "scope_sha256": sha256(output / "scope.json")},
        "source_input_sha256": fingerprints, "observations": len(observations), "rows": len(rows),
        "manual_reviews_sha256": sha256(REVIEW_PATH),
        "modeling_candidates": len(candidates), "source_checked_candidates": len(checked),
        "exact_price_agreement_candidates": sum(row["source_price_verified"] for row in checked),
        "manual_price_accepted_candidates": sum(row["manual_price_accepted"] for row in checked),
        "history_parent": str(args.parent_evaluation.resolve()), "history_parent_manifest_sha256": sha256(args.parent_evaluation / "manifest.json"),
        "history_policy": "preserve_partitions_quarantine_collisions", "selection": "latest timestamp per listing; no fallback to older checked targets",
        "catalogue_additions": len(additions), "raw_preserved": True, "training_status": "not_run",
        "batch_counts": {batch.name: len(members) for batch, members, _ in batches},
        "output_sha256": {path.name: sha256(path) for path in output.iterdir()},
        "report_sha256": {str(path.relative_to(report)): sha256(path) for path in report.rglob("*") if path.is_file()},
        "code_sha256": {name: sha256(PROJECT_ROOT / name) for name in (
            "scripts/prepare_modeling_dataset.py", "pilot/consolidate.py", "pilot/quality.py", "pilot/evidence.py", "pilot/identity.py", "pilot/reviews.py")},
    }
    save_json(output / "manifest.json", manifest)
    return manifest


def prepare_modeling_dataset(args):
    output, report = args.output_dir.resolve(), args.report_dir.resolve()
    sources = [path.resolve() for path in args.batch_dir] + [args.parent_evaluation.resolve()]
    if output.exists() or report.exists():
        raise ValueError("Dataset/report already exists; use new version directories")
    for target in (output, report):
        if target.is_relative_to(PROJECT_ROOT / "data/raw") or any(
            target.is_relative_to(source) or source.is_relative_to(target) for source in sources
        ):
            raise ValueError("Outputs must be separate from raw inputs and parent artifacts")
    if output.is_relative_to(report) or report.is_relative_to(output):
        raise ValueError("Dataset and report outputs must be separate")
    history = verify_parent(args.parent_evaluation)
    fingerprints = input_hashes(args.batch_dir, args.catalogue, args.scope, args.parent_evaluation)
    fingerprints[str(REVIEW_PATH.resolve())] = sha256(REVIEW_PATH)
    manual_reviews = load_reviews(REVIEW_PATH)
    catalogue = load_catalogue(args.catalogue)
    scope = json.loads(args.scope.read_text(encoding="utf-8"))
    batches = []
    # Evidence reports also serve as checkpoints if later preparation rejects data.
    report.mkdir(parents=True)
    for batch in args.batch_dir:
        print(f"Auditing saved batch {batch.name}", flush=True)
        members = audit_batch(batch)
        evidence = review_evidence(batch, members)
        save_json(report / f"{batch.name}_evidence.json", evidence)
        batches.append((batch, members, evidence))
        print(f"Verified {len(evidence)} cached pages for {batch.name}", flush=True)
    catalogue, additions = expand_catalogue(catalogue, batches)
    observations = []
    evidence_by_batch = {batch.name: evidence for batch, _, evidence in batches}
    for batch, members, evidence in batches:
        prepared = prepare_rows(members, catalogue, scope, evidence)
        for row in prepared:
            row["source_batch"] = batch.name
        prepared = apply_reviews(prepared, manual_reviews, evidence_by_batch)
        observations.extend(prepared)
        summary = render_quality_report(prepared, evidence, {})
        accepted = sum(row["manual_price_accepted"] for row in prepared)
        summary += (f"\n## Applied manual review\n\nExplicit exclusions and corrections follow the saved manual-review file. "
                    f"{accepted} rows have a user-accepted displayed/structured price pair. "
                    "Those eligible rows enter the checked population by manual acceptance; their exact source-agreement flag remains false. "
                    "Registration year stays metadata only.\n")
        (report / f"{batch.name}_quality.md").write_text(summary, encoding="utf-8")
    rows, decisions = consolidate_observations(observations, history)
    rows = apply_reviews(rows, manual_reviews, evidence_by_batch)
    by_id = {row["listing_id"]: row for row in rows}
    for item in decisions:
        item["exclusion_reasons"] = by_id[item["listing_id"]]["exclusion_reasons"]
    if any(sha256(Path(path)) != expected for path, expected in fingerprints.items()):
        raise ValueError("Input files changed during preparation")
    return save_dataset(output, report, observations, rows, decisions, catalogue, additions, batches, fingerprints, args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, nargs="+", default=[PROJECT_ROOT / "data/raw/pilot_batch_001", PROJECT_ROOT / "data/raw/modeling_batch_002"])
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/processed/modeling_combined_002_v1")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports/pilot/modeling_combined_002_v1")
    parser.add_argument("--parent-evaluation", type=Path, default=PROJECT_ROOT / "data/processed/pilot_batch_001_eval_v1")
    parser.add_argument("--catalogue", type=Path, default=PROJECT_ROOT / "catalogues/cars.json")
    parser.add_argument("--scope", type=Path, default=PROJECT_ROOT / "configs/pilot_scope.json")
    result = prepare_modeling_dataset(parser.parse_args())
    print(f"Prepared {result['rows']} unique listings from {result['observations']} observations; {result['source_checked_candidates']} checked candidates", flush=True)


if __name__ == "__main__":
    main()
