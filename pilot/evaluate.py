"""Load frozen evaluation inputs with provenance and default test isolation."""

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pilot.features import feature_contract, prepare_input, prepare_target
from pilot.identity import load_catalogue
from pilot.splits import validate_splits

POPULATION = "source_checked_candidates.csv"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_population(dataset_dir: Path, catalogue_path: Path, scope_path: Path) -> tuple:
    """Check prepared-data provenance before exposing the eligible population."""
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("preparation_schema_version") != 1 or manifest.get("status", "").startswith("superseded"):
        raise ValueError("Dataset preparation version is unsupported or superseded")
    checks = {
        dataset_dir / POPULATION: manifest["output_sha256"][POPULATION],
        catalogue_path: manifest["input_fingerprints"]["catalogue_sha256"],
        scope_path: manifest["input_fingerprints"]["scope_sha256"],
    }
    for path, expected in checks.items():
        if sha256(path) != expected:
            raise ValueError(f"Dataset/configuration checksum mismatch: {path.name}")
    with (dataset_dir / POPULATION).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != manifest["source_checked_candidates"]:
        raise ValueError("Source-checked population count differs from its manifest")
    for row in rows:
        if row.get("source_checked_candidate") != "True" or row.get("source_price_verified") != "True" or row.get("exclusion_reasons"):
            raise ValueError("Evaluation population includes an ineligible or unchecked row")
    return rows, load_catalogue(catalogue_path), json.loads(scope_path.read_text(encoding="utf-8")), manifest


@dataclass(frozen=True)
class EvaluationData:
    """Aligned arrays for later estimators; metadata never enters the inputs."""

    listing_ids: tuple[str, ...]
    group_ids: tuple[str, ...]
    validation_folds: tuple[int | None, ...]
    inputs: tuple[dict, ...]
    targets: tuple[int, ...]


def load_evaluation_data(dataset_dir: Path, evaluation_dir: Path, feature_set: str,
                         partition: str = "development") -> EvaluationData:
    """Load the same saved membership for every model and feature set.

    Test data requires explicit partition='demo_test'. Future comparison commands
    must use the default development partition until a candidate is frozen.
    """
    if partition not in {"development", "demo_test"}:
        raise ValueError("Unknown evaluation partition")
    manifest = json.loads((evaluation_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("evaluation_schema_version") != 1:
        raise ValueError("Unsupported evaluation artifact")
    for name in ("splits.json", "feature_contract.json", "catalogue.json", "scope.json", "config.json"):
        if sha256(evaluation_dir / name) != manifest["output_sha256"][name]:
            raise ValueError(f"Evaluation artifact checksum mismatch: {name}")
    if sha256(dataset_dir / "manifest.json") != manifest["dataset_manifest_sha256"]:
        raise ValueError("Dataset manifest changed after evaluation was frozen")
    if sha256(dataset_dir / POPULATION) != manifest["population_sha256"]:
        raise ValueError("Evaluation population changed after splits were frozen")
    for name in ("features.py", "identity.py", "evidence.py"):
        if sha256(Path(__file__).with_name(name)) != manifest["code_sha256"][f"pilot/{name}"]:
            raise ValueError("Feature implementation changed; create a new evaluation version")
    contract = json.loads((evaluation_dir / "feature_contract.json").read_text(encoding="utf-8"))
    if contract != feature_contract():
        raise ValueError("Feature contract changed; create a new evaluation version")
    rows, catalogue, scope, _ = load_population(dataset_dir, evaluation_dir / "catalogue.json", evaluation_dir / "scope.json")
    splits = json.loads((evaluation_dir / "splits.json").read_text(encoding="utf-8"))
    validate_splits(rows, splits)
    by_id = {row["listing_id"]: row for row in rows}
    chosen = [item for item in splits["assignments"] if item["partition"] == partition]
    selected = [by_id[item["listing_id"]] for item in chosen]
    return EvaluationData(
        listing_ids=tuple(item["listing_id"] for item in chosen),
        group_ids=tuple(item["group_id"] for item in chosen),
        validation_folds=tuple(item["validation_fold"] for item in chosen),
        inputs=tuple(prepare_input(row, feature_set, catalogue, scope) for row in selected),
        targets=tuple(prepare_target(row) for row in selected),
    )
