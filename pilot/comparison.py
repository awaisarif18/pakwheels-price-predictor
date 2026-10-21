"""Run the fixed M3 matrix against development folds and save a private ledger."""

import csv
import json
import platform
import sys
import warnings
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path
from time import perf_counter

import numpy as np

from pilot.evaluate import load_evaluation_data, sha256
from pilot.features import FEATURE_SETS, NUMERICAL_FIELDS
from pilot.metrics import regression_metrics, summarize_predictions
from pilot.model_report import comparison_report
from pilot.models import build_candidate, input_frame, preprocessing_policy
from pilot.paths import PROJECT_ROOT


def read_experiments(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("version") != 1 or config.get("target") != "raw_pkr":
        raise ValueError("Use experiment version 1 and raw_pkr targets")
    if config.get("feature_sets") != list(FEATURE_SETS):
        raise ValueError("Initial comparison requires the fixed F0/F1/F2 matrix")
    if set(config.get("candidates", {})) != {"median", "ridge", "random_forest", "catboost"}:
        raise ValueError("Initial comparison requires median, Ridge, Random Forest, and CatBoost")
    seed = config.get("seed")
    if type(seed) is not int or seed < 0 or not config.get("experiment_id"):
        raise ValueError("Experiment needs a nonnegative integer seed and an ID")
    minimum = config["candidates"]["median"].get("min_group_size")
    if type(minimum) is not int or minimum < 1:
        raise ValueError("Median minimum group size must be a positive integer")
    return config


def fold_indices(data):
    """Recheck fold/group isolation at the fit boundary, including synthetic inputs."""
    folds = data.validation_folds
    if not folds or any(type(fold) is not int for fold in folds) or len(set(folds)) < 2:
        raise ValueError("Comparison requires assigned development folds")
    for fold in sorted(set(folds)):
        train = [i for i, assigned in enumerate(folds) if assigned != fold]
        validation = [i for i, assigned in enumerate(folds) if assigned == fold]
        if {data.group_ids[i] for i in train} & {data.group_ids[i] for i in validation}:
            raise ValueError("Training and validation groups overlap")
        yield fold, train, validation


def fitted_details(model, name: str) -> dict:
    if name == "median":
        return {"fitted_median_group_counts": [len(level) for level in model.medians_]}
    if name == "catboost":
        return {"effective_parameters": model.get_all_params()}
    preprocessing = model.named_steps["preprocess"]
    numeric = preprocessing.named_transformers_["numeric"]
    categorical = preprocessing.named_transformers_["categorical"]
    details = {
        "effective_parameters": model.named_steps["model"].get_params(),
        "imputation_values": numeric.named_steps["impute"].statistics_.tolist(),
        "categorical_vocabulary": [values.tolist() for values in categorical.categories_],
    }
    if "scale" in numeric.named_steps:
        scaler = numeric.named_steps["scale"]
        details.update(scale_mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist())
    return details


def held_out_rows(data, metadata, frame, train, validation, estimates, experiment, fold):
    training = [metadata[i] for i in train]
    variants = {(row["make"], row["model"], row["variant"]) for row in training}
    cities = {row["listing_city"] for row in training}
    categories = {field: set(frame.iloc[train][field]) for field in frame if field not in NUMERICAL_FIELDS}
    records = []
    for index, estimate in zip(validation, estimates):
        row = metadata[index]
        records.append({
            "experiment": experiment, "fold": fold, "listing_id": data.listing_ids[index],
            "group_id": data.group_ids[index], "family": row["make"] + " " + row["model"],
            "variant": row["variant"], "year": row["year"], "listing_city": row["listing_city"],
            "actual_pkr": data.targets[index], "predicted_pkr": float(estimate),
            "absolute_error_pkr": abs(float(estimate) - data.targets[index]),
            "unseen_variant": (row["make"], row["model"], row["variant"]) not in variants,
            "unseen_city": row["listing_city"] not in cities,
            "unseen_input_categories": ";".join(field for field, values in categories.items() if row[field] not in values),
        })
    return records


def compare_candidate(data, metadata, feature_set: str, name: str, parameters: dict, seed: int,
                      *, columns=None, experiment_id=None):
    frame = input_frame(data.inputs, feature_set, columns=columns)
    targets = np.asarray(data.targets, dtype=float)
    experiment = experiment_id or f"{name}_{feature_set}"
    predictions, fold_results, details = [], [], []
    for fold, train, validation in fold_indices(data):
        model = (build_candidate(name, feature_set, parameters, seed) if columns is None else
                 build_candidate(name, feature_set, parameters, seed, columns=columns))
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            started = perf_counter()
            model.fit(frame.iloc[train], targets[train])
            fit_seconds = perf_counter() - started
            started = perf_counter()
            estimates = model.predict(frame.iloc[validation])
            predict_seconds = perf_counter() - started
        metrics = regression_metrics(targets[validation], estimates)
        fold_results.append({"experiment": experiment, "fold": fold, "training_rows": len(train),
                             **metrics, "fit_seconds": fit_seconds, "predict_seconds": predict_seconds})
        details.append({"experiment": experiment, "fold": fold,
                        "input_columns": list(frame.columns),
                        "training_ids": [data.listing_ids[i] for i in train],
                        "validation_ids": [data.listing_ids[i] for i in validation],
                        "warnings": [str(item.message) for item in captured],
                        **fitted_details(model, name)})
        predictions.extend(held_out_rows(data, metadata, frame, train, validation, estimates, experiment, fold))
    return predictions, fold_results, details


def overall_results(predictions, fold_results):
    results = []
    baseline = [row for row in predictions if row["experiment"] == "median_F0"]
    baseline_mae = regression_metrics([row["actual_pkr"] for row in baseline],
                                      [row["predicted_pkr"] for row in baseline])["mae_pkr"]
    for experiment in sorted({row["experiment"] for row in predictions}):
        rows = [row for row in predictions if row["experiment"] == experiment]
        folds = [row for row in fold_results if row["experiment"] == experiment]
        baseline_folds = [next(row for row in fold_results if row["experiment"] == "median_F0" and row["fold"] == item["fold"]) for item in folds]
        metrics = regression_metrics([row["actual_pkr"] for row in rows], [row["predicted_pkr"] for row in rows])
        results.append({"experiment": experiment, **metrics,
                        "fold_mae_min_pkr": min(row["mae_pkr"] for row in folds),
                        "fold_mae_max_pkr": max(row["mae_pkr"] for row in folds),
                        "baseline_improvement_pct": 100 * (baseline_mae - metrics["mae_pkr"]) / baseline_mae if baseline_mae else None,
                        "folds_better_than_baseline": sum(row["mae_pkr"] < other["mae_pkr"] for row, other in zip(folds, baseline_folds)),
                        "fit_seconds": sum(row["fit_seconds"] for row in folds)})
    return results


def save_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def comparison_manifest(dataset, evaluation, config_path, config, reference, fingerprints):
    evaluation_manifest = json.loads((evaluation / "manifest.json").read_text(encoding="utf-8"))
    dataset_manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    return {
        "comparison_schema_version": 1, "experiment_id": config["experiment_id"],
        "created_at": datetime.now(timezone.utc).isoformat(), "dataset_id": dataset_manifest["dataset_id"],
        "split_id": evaluation_manifest["split_id"], "development_rows": len(reference.targets),
        "test_status": "reserved_unopened_for_model_outcomes", "input_sha256": fingerprints,
        "config_sha256": sha256(config_path), "status": "exploratory_no_demo_support",
        "code_sha256": {name: sha256(PROJECT_ROOT / name) for name in (
            "pilot/models.py", "pilot/metrics.py", "pilot/comparison.py", "pilot/model_report.py",
            "pilot/evaluate.py", "scripts/compare_models.py", "requirements-modeling.txt")},
        "preprocessing": {name: preprocessing_policy(name) for name in config["candidates"]},
    }


def write_comparison(output, manifest, config, predictions, folds, fitted):
    results = overall_results(predictions, folds)
    subgroups = summarize_predictions(predictions)
    # Render before creating the output, so formatting errors leave no partial run.
    report = comparison_report(manifest, results, subgroups, predictions)
    output.mkdir(parents=True)
    for filename, rows in {"predictions.csv": predictions, "fold_metrics.csv": folds,
                           "summary.csv": results, "subgroup_metrics.csv": subgroups}.items():
        save_csv(output / filename, rows)
    save_json(output / "config.json", config)
    save_json(output / "fold_details.json", fitted)
    save_json(output / "environment.json", {"python": sys.version, "platform": platform.platform(),
              "packages": {item.metadata["Name"]: item.version for item in distributions()}})
    (output / "model_selection.md").write_text(report, encoding="utf-8")
    manifest["output_sha256"] = {path.name: sha256(path) for path in output.iterdir()}
    save_json(output / "manifest.json", manifest)


def run_comparison(dataset: Path, evaluation: Path, output: Path, config_path: Path) -> dict:
    dataset, evaluation, output = dataset.resolve(), evaluation.resolve(), output.resolve()
    if output.exists():
        raise ValueError("Comparison output already exists; choose a new directory")
    if output.is_relative_to(PROJECT_ROOT / "data/raw") or any(
        output.is_relative_to(source) or source.is_relative_to(output) for source in (dataset, evaluation)
    ):
        raise ValueError("Comparison output must be separate from raw data and input artifacts")
    config = read_experiments(config_path)
    input_paths = [config_path] + [path for source in (dataset, evaluation) for path in source.iterdir() if path.is_file()]
    fingerprints = {str(path): sha256(path) for path in input_paths}
    data = {name: load_evaluation_data(dataset, evaluation, name) for name in config["feature_sets"]}
    reference = data["F2"]
    for item in data.values():
        if (item.listing_ids, item.targets, item.validation_folds, item.group_ids) != (
            reference.listing_ids, reference.targets, reference.validation_folds, reference.group_ids
        ):
            raise ValueError("Feature sets must share identical development membership")
    predictions, folds, fitted = [], [], []
    for feature_set in config["feature_sets"]:
        for name, parameters in config["candidates"].items():
            print(f"Comparing {name}_{feature_set} on development folds", flush=True)
            rows, metrics, details = compare_candidate(data[feature_set], reference.inputs, feature_set, name, parameters, config["seed"])
            predictions.extend(rows)
            folds.extend(metrics)
            fitted.extend(details)
    if any(sha256(Path(path)) != expected for path, expected in fingerprints.items()):
        raise ValueError("Input artifacts changed during comparison")
    manifest = comparison_manifest(dataset, evaluation, config_path, config, reference, fingerprints)
    write_comparison(output, manifest, config, predictions, folds, fitted)
    return manifest
