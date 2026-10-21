"""One-time reserved-test evaluation of an already frozen saved candidate."""

from datetime import datetime, timezone
import json

import numpy as np

from pilot.comparison import save_csv
from pilot.demo_artifacts import (
    finish_artifact, input_hashes, output_path, read_json, save_json, usage_path, verify_artifact, verify_inputs,
)
from pilot.evaluate import load_evaluation_data, sha256
from pilot.models import ComparableMedian, input_frame
from pilot.predictor import SavedPredictor
from pilot.predictor_inputs import load_predictor_development, predictor_frame
from pilot.qualification import error_report, score_rows
from pilot.support import family_name, support_reason


def evaluate_demo(dataset, evaluation, bundle, output, *, usage_dir=None):
    output = output_path(output, (dataset, evaluation, bundle))
    predictor = SavedPredictor(bundle)
    frozen = predictor.manifest
    verify_inputs(frozen)
    evaluation_manifest = verify_artifact(evaluation)
    if evaluation_manifest["split_id"] != frozen["split_id"] or frozen["input_sha256"].get(
        str((dataset / "manifest.json").resolve())
    ) != sha256(dataset / "manifest.json"):
        raise ValueError("Final evaluation must use the frozen dataset and split")
    policy = read_json(bundle / "candidate.json")
    marker = usage_path(frozen["split_id"], usage_dir)
    if marker.exists():
        raise ValueError("This reserved test has already been opened; its outcomes cannot be reopened for selection")
    marker.parent.mkdir(parents=True, exist_ok=True)
    claim = {"split_id": frozen["split_id"], "candidate_id": frozen["candidate_id"],
             "bundle_manifest_sha256": sha256(bundle / "manifest.json"), "status": "opened_scoring_started",
             "opened_at": datetime.now(timezone.utc).isoformat(), "output_dir": str(output)}
    with marker.open("x", encoding="utf-8") as handle:
        json.dump(claim, handle, indent=2)
    # The usage claim is durable even if scoring fails. Never silently reopen.
    test = load_evaluation_data(dataset, evaluation, "F2", partition="demo_test")
    development = load_predictor_development(dataset, evaluation)
    if set(test.group_ids) & set(development.group_ids) or set(test.listing_ids) & set(development.listing_ids):
        raise ValueError("Reserved test overlaps development")
    estimates = predictor.model.predict(predictor_frame(test.inputs, contract=predictor.contract))
    median = ComparableMedian(policy["baseline_min_group_size"]).fit(input_frame(development.inputs, "F0"), np.asarray(development.targets))
    baseline_estimates = median.predict(input_frame(test.inputs, "F0"))
    predictions, reference = [], {}
    for index, row in enumerate(test.inputs):
        reason = support_reason(row, predictor.support)
        record = {"listing_id": test.listing_ids[index], "group_id": test.group_ids[index], "family": family_name(row),
                  "variant": row["variant"], "year": row["year"], "listing_city": row["listing_city"],
                  "actual_pkr": test.targets[index], "predicted_pkr": float(estimates[index]),
                  "supported": reason is None, "unsupported_reason": reason or ""}
        predictions.append(record)
        reference[record["listing_id"]] = {**record, "predicted_pkr": float(baseline_estimates[index])}
    supported = [row for row in predictions if row["supported"]]
    report = error_report(supported, reference, policy, policy["test_min_supported_rows"], policy["test_min_supported_family_rows"])
    report.update(full_test_metrics=score_rows(predictions), full_baseline_metrics=score_rows(list(reference.values())),
                  reserved_test_rows=len(predictions), supported_test_rows=len(supported))
    fingerprints = input_hashes([path for root in (dataset, evaluation, bundle) for path in root.iterdir() if path.is_file()])
    output.mkdir(parents=True)
    save_csv(output / "predictions.csv", predictions)
    save_json(output / "metrics.json", report)
    save_json(output / "baseline_predictions.json", list(reference.values()))
    (output / "evaluation.md").write_text(
        "# Frozen predictor test evaluation\n\n"
        f"Candidate `{frozen['candidate_id']}`. Gate passed: {report['passed']}.\n\n"
        f"Reserved rows: {len(predictions)}. Supported rows: {len(supported)}. "
        f"Full-test MAE: PKR {report['full_test_metrics']['mae_pkr']:,.0f}.\n\n"
        "The supported subset and limits were frozen before opening outcomes. No support or model changes follow these results. "
        "If these outcomes guide tuning, this test becomes development evidence and a new independent holdout is required.\n",
        encoding="utf-8")
    manifest = finish_artifact(output, {"kind": "demo_test", "candidate_id": frozen["candidate_id"], "split_id": frozen["split_id"],
                              "bundle_manifest_sha256": sha256(bundle / "manifest.json"), "passed": report["passed"],
                              "test_status": "opened_scored_frozen_candidate"}, fingerprints,
                             ("pilot/demo_evaluation.py", "pilot/qualification.py", "pilot/support.py"))
    save_json(marker, {**claim, "status": "completed", "passed": report["passed"], "result_manifest_sha256": sha256(output / "manifest.json")})
    return manifest
