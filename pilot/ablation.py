"""Fixed independent feature removals with verified historical references."""

import csv
import json
import math
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path

from pilot.ablation_report import ablation_report, removal_specs, summarize_ablation
from pilot.comparison import compare_candidate, save_csv, save_json
from pilot.evaluate import load_evaluation_data, sha256
from pilot.features import FEATURE_SETS
from pilot.metrics import regression_metrics
from pilot.paths import PROJECT_ROOT

REMOVALS = ("listing_city", "year", "mileage_km", "variant", "fuel", "transmission", "engine_cc", "assembly", "body_type")


def read_config(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("version") not in (1, 2) or config.get("base_feature_set") != "F2" or config.get("target") != "raw_pkr":
        raise ValueError("Ablation requires version 1 or 2, F2 inputs, and raw_pkr targets")
    if config["version"] == 1:
        if config.get("remove_individually") != list(REMOVALS) or "remove_together" in config:
            raise ValueError("Use the nine fixed independent removals, starting with listing_city")
    elif config.get("remove_together") != ["fuel", "body_type"] or "remove_individually" in config:
        raise ValueError("Combined confirmation must remove only fuel and body_type together")
    if list(config.get("candidates", {})) != ["catboost", "random_forest"]:
        raise ValueError("Ablation requires CatBoost followed by Random Forest")
    if type(config.get("seed")) is not int or config["seed"] < 0 or not config.get("experiment_id"):
        raise ValueError("Ablation requires a nonnegative integer seed and experiment ID")
    if config.get("reference_tolerance_pkr") != 0.01:
        raise ValueError("Reference tolerance must be PKR 0.01")
    limits = config.get("max_mae_increase_pct", {})
    if set(limits) != {"overall", "fold", "family"} or any(
        type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in limits.values()
    ):
        raise ValueError("MAE limits must be finite nonnegative overall/fold/family percentages")
    return config


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_reference(reference, dataset, evaluation, config):
    manifest = json.loads((reference / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["output_sha256"].items():
        if sha256(reference / name) != expected:
            raise ValueError(f"Reference artifact checksum mismatch: {name}")
    for name, expected in manifest["input_sha256"].items():
        if sha256(Path(name)) != expected:
            raise ValueError(f"Reference input checksum mismatch: {name}")
    for source in (dataset, evaluation):
        if manifest["input_sha256"].get(str(source / "manifest.json")) != sha256(source / "manifest.json"):
            raise ValueError("Reference must use the same dataset and evaluation manifests")
    previous = json.loads((reference / "config.json").read_text(encoding="utf-8"))
    if any(config[key] != previous[key] for key in ("seed", "target")) or any(
        config["candidates"][name] != previous["candidates"][name] for name in config["candidates"]
    ):
        raise ValueError("Ablation must preserve reference model settings, seed, and target")
    if manifest["test_status"] != "reserved_unopened_for_model_outcomes":
        raise ValueError("Reference must be development-only")
    return read_csv(reference / "predictions.csv")


def check_reference(model, rows, previous, data, tolerance):
    old = [row for row in previous if row["experiment"] == f"{model}_F2"]
    by_id = {row["listing_id"]: row for row in old}
    if len(old) != len(data.listing_ids) or set(by_id) != set(data.listing_ids):
        raise ValueError("Reference development membership differs")
    max_difference = 0.0
    for row in rows:
        other = by_id[row["listing_id"]]
        if float(other["actual_pkr"]) != row["actual_pkr"] or int(other["fold"]) != row["fold"] or other["group_id"] != row["group_id"]:
            raise ValueError("Reference targets, groups, or folds differ")
        max_difference = max(max_difference, abs(float(other["predicted_pkr"]) - row["predicted_pkr"]))
    original = regression_metrics([float(row["actual_pkr"]) for row in old], [float(row["predicted_pkr"]) for row in old])
    current = regression_metrics([row["actual_pkr"] for row in rows], [row["predicted_pkr"] for row in rows])
    metric_difference = max(abs(original[key] - current[key]) for key in ("mae_pkr", "median_ae_pkr", "rmse_pkr"))
    if max_difference > tolerance or metric_difference > tolerance:
        raise ValueError(f"Full {model} reference did not reproduce within PKR {tolerance}")
    return {"model": model, "max_prediction_difference_pkr": max_difference,
            "max_metric_difference_pkr": metric_difference, "passed": True}


def save_ablation(output, manifest, config, predictions, folds, fitted, checks):
    summary, subgroups, changes = summarize_ablation(predictions, folds, fitted, config)
    report = ablation_report(manifest, summary, config)
    output.mkdir(parents=True)
    for name, rows in {"predictions.csv": predictions, "fold_metrics.csv": folds, "summary.csv": summary,
                       "subgroup_metrics.csv": subgroups, "subgroup_changes.csv": changes, "reference_checks.csv": checks}.items():
        save_csv(output / name, rows)
    save_json(output / "fold_details.json", fitted)
    save_json(output / "config.json", config)
    save_json(output / "environment.json", {"python": sys.version, "platform": platform.platform(),
              "packages": {item.metadata["Name"]: item.version for item in distributions()}})
    (output / "ablation_report.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {path.name: sha256(path) for path in output.iterdir()}
    save_json(output / "manifest.json", manifest)


def run_ablation(dataset, evaluation, reference, output, config_path):
    dataset, evaluation, reference, output, config_path = [path.resolve() for path in (dataset, evaluation, reference, output, config_path)]
    if output.exists():
        raise ValueError("Ablation output already exists; choose a new directory")
    if output.is_relative_to(PROJECT_ROOT / "data/raw") or any(
        output.is_relative_to(source) or source.is_relative_to(output) for source in (dataset, evaluation, reference)
    ):
        raise ValueError("Ablation output must be separate from raw data and input artifacts")
    config = read_config(config_path)
    inputs = [config_path] + [path for root in (dataset, evaluation, reference) for path in root.iterdir() if path.is_file()]
    fingerprints = {str(path): sha256(path) for path in inputs}
    previous = verify_reference(reference, dataset, evaluation, config)
    data = load_evaluation_data(dataset, evaluation, "F2")
    predictions, folds, fitted, checks = [], [], [], []
    for label, removed in [("full", ())] + removal_specs(config):
        columns = tuple(field for field in FEATURE_SETS["F2"] if field not in removed)
        for model, parameters in config["candidates"].items():
            experiment = f"{model}_full" if label == "full" else f"{model}_without_{label}"
            print(f"Comparing {experiment} on development folds", flush=True)
            rows, metrics, details = compare_candidate(data, data.inputs, "F2", model, parameters, config["seed"],
                                                       columns=columns, experiment_id=experiment)
            if label == "full":
                checks.append(check_reference(model, rows, previous, data, config["reference_tolerance_pkr"]))
                print(f"Verified {model} full reference", flush=True)
            predictions.extend(rows)
            folds.extend(metrics)
            fitted.extend(details)
    if any(sha256(Path(path)) != expected for path, expected in fingerprints.items()):
        raise ValueError("Input artifacts changed during ablation")
    manifest = ablation_manifest(dataset, evaluation, reference, data, config, fingerprints)
    save_ablation(output, manifest, config, predictions, folds, fitted, checks)
    return manifest


def ablation_manifest(dataset, evaluation, reference, data, config, fingerprints):
    return {
        "ablation_schema_version": 1, "experiment_id": config["experiment_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_id": json.loads((dataset / "manifest.json").read_text())["dataset_id"],
        "split_id": json.loads((evaluation / "manifest.json").read_text())["split_id"],
        "reference_experiment_id": json.loads((reference / "manifest.json").read_text())["experiment_id"],
        "development_rows": len(data.targets), "configurations": len(config["candidates"]) * (1 + len(removal_specs(config))),
        "test_status": "reserved_unopened_for_model_outcomes", "status": "complete_exploratory_no_schema_adopted",
        "input_sha256": fingerprints,
        "code_sha256": {name: sha256(PROJECT_ROOT / name) for name in (
            "pilot/ablation.py", "pilot/ablation_report.py", "pilot/comparison.py", "pilot/models.py",
            "pilot/metrics.py", "pilot/evaluate.py", "pilot/reviews.py", "pilot/features.py",
            "scripts/ablate_features.py", "requirements-modeling.txt")},
    }
