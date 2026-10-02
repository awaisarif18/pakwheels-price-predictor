"""Freeze offline feature contracts and group-aware splits; do not fit models."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pilot.evaluate import POPULATION, load_population, sha256
from pilot.features import FEATURE_SETS, feature_contract, prepare_input, prepare_target
from pilot.paths import PROJECT_ROOT
from pilot.splits import build_splits, split_counts


def save_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_evaluation(dataset: Path, output: Path, config_path: Path,
                       catalogue_path: Path, scope_path: Path) -> dict:
    """Create a new version only after eligibility and split checks pass."""
    dataset, output = dataset.resolve(), output.resolve()
    if output.exists():
        raise ValueError("Evaluation output already exists; choose a new directory")
    if output.is_relative_to(PROJECT_ROOT / "data/raw") or output.is_relative_to(dataset) or dataset.is_relative_to(output):
        raise ValueError("Evaluation output must be separate from the input dataset and raw data")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("version") != 1 or config.get("population") != POPULATION:
        raise ValueError("Use evaluation config version 1 and the source-checked population")
    rows, catalogue, scope, dataset_manifest = load_population(dataset, catalogue_path, scope_path)
    # Validate all feature sets on the same eligible rows, never filter by set.
    for row in rows:
        for feature_set in FEATURE_SETS:
            prepare_input(row, feature_set, catalogue, scope)
        prepare_target(row)
    splits = build_splits(rows, config)
    code_hashes = {name: sha256(PROJECT_ROOT / name) for name in (
        "pilot/features.py", "pilot/identity.py", "pilot/evidence.py", "pilot/splits.py",
        "pilot/evaluate.py", "scripts/prepare_evaluation.py")}
    identity = {
        "dataset_manifest_sha256": sha256(dataset / "manifest.json"),
        "population_sha256": sha256(dataset / POPULATION), "config_sha256": sha256(config_path),
        "feature_contract": feature_contract(), "code_sha256": code_hashes,
    }
    split_id = "pilot_eval_" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    splits["split_id"] = split_id
    counts = split_counts(rows, splits)
    # Recheck the immutable inputs before writing anything.
    load_population(dataset, catalogue_path, scope_path)
    output.mkdir(parents=True)
    for name, value in {
        "splits.json": splits, "feature_contract.json": feature_contract(),
        "catalogue.json": catalogue, "scope.json": scope, "config.json": config,
    }.items():
        # Catalogue/scope hashes must continue to match the prepared manifest.
        if name in {"catalogue.json", "scope.json"}:
            output.joinpath(name).write_bytes((catalogue_path if name == "catalogue.json" else scope_path).read_bytes())
        else:
            save_json(output / name, value)
    partition_counts = Counter(item["partition"] for item in splits["assignments"])
    fold_counts = Counter(item["validation_fold"] for item in splits["assignments"] if item["partition"] == "development")
    report = [
        "# Fixed exploratory evaluation splits", "",
        f"Split ID: `{split_id}`. Dataset: `{dataset_manifest['dataset_id']}`.", "",
        f"Population: {len(rows)} source-checked rows. Development: {partition_counts['development']}. Reserved demo test: {partition_counts['demo_test']}.",
        f"Development validation-fold counts: {dict(sorted(fold_counts.items()))}.", "",
        "| Family | Partition | Validation fold | Rows | Groups |",
        "|---|---|---:|---:|---:|",
    ]
    for item in counts:
        fold = item["validation_fold"] if item["validation_fold"] is not None else "n/a"
        report.append(f"| {item['family']} | {item['partition']} | {fold} | {item['rows']} | {item['groups']} |")
    report += [
        "", "## Rules and limits", "",
        f"Seeded SHA-256 ordering allocates the nearest {config['test_fraction']:.0%} group quota per family, then balances development folds by family/global row counts. Group membership remains intact. Targets do not influence allocation.",
        "Only family is stratified. Variant, year, city, and price coverage may be sparse or uneven; inspect development coverage and report unseen categories during later validation.",
        "Each development row validates once; the remaining development folds train. The demo test is excluded from every development fold.",
        "F0, F1, and F2 share exact row membership. Numerical missing values remain null; missing categorical values use a fixed token. No fitted imputation, encoding, scaling, target transform, model, or score exists.",
        "The test is reserved and unopened for model outcomes. Few test groups per family make later errors exploratory and unstable. This split does not establish demo support or chronological generalization.",
        "Use the development loader by default. Open demo_test only after freezing the candidate; if its results guide further tuning, retire its untouched status and obtain a new independent test.",
    ]
    (output / "split_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    manifest = {
        "evaluation_schema_version": 1, "split_id": split_id,
        "created_at": datetime.now(timezone.utc).isoformat(), "dataset_id": dataset_manifest["dataset_id"],
        "dataset_manifest_sha256": identity["dataset_manifest_sha256"],
        "population_sha256": identity["population_sha256"], "code_sha256": code_hashes,
        "population_rows": len(rows), "partition_rows": dict(partition_counts),
        "family_partition_counts": counts, "status": "exploratory_small_sample",
        "test_status": "reserved_unopened", "model_status": "not_trained",
        "output_sha256": {name: sha256(output / name) for name in (
            "splits.json", "feature_contract.json", "catalogue.json", "scope.json", "config.json", "split_report.md")},
    }
    save_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=PROJECT_ROOT / "data/processed/pilot_batch_001_v2")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/processed/pilot_batch_001_eval_v1")
    parser.add_argument("--config", type=Path, default=PROJECT_ROOT / "configs/evaluation_pilot.json")
    parser.add_argument("--catalogue", type=Path, default=PROJECT_ROOT / "catalogues/cars.json")
    parser.add_argument("--scope", type=Path, default=PROJECT_ROOT / "configs/pilot_scope.json")
    args = parser.parse_args()
    try:
        result = prepare_evaluation(args.dataset_dir, args.output_dir, args.config, args.catalogue, args.scope)
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))
    print(f"Frozen {result['split_id']}: {result['partition_rows']}")
    print(f"Evaluation artifacts: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
