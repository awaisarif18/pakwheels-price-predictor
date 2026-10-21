"""Freeze a local-demo candidate using development evidence only."""

import math

from pilot.ablation import read_csv, verify_reference
from pilot.comparison import save_csv
from pilot.demo_artifacts import (
    finish_artifact, input_hashes, output_path, read_json, save_json, usage_path, verify_artifact, verify_inputs,
)
from pilot.metrics import regression_metrics
from pilot.predictor_inputs import DEFAULT_CONTRACT, load_predictor_contract, load_predictor_development
from pilot.support import build_support, family_name, support_reason


def score_rows(rows):
    if not rows:
        return None
    return regression_metrics([float(row["actual_pkr"]) for row in rows], [float(row["predicted_pkr"]) for row in rows])


def error_report(rows, baseline, policy, minimum_rows, minimum_family_rows):
    """Use the same frozen limits for development selection and final test."""
    checks, results = [], {}
    limits = policy["errors"]
    groups = {"overall": rows, **{family: [row for row in rows if row["family"] == family]
                                  for family in limits["family_mae_pkr"]}}
    for family, selected in groups.items():
        minimum = minimum_rows if family == "overall" else minimum_family_rows
        metric = score_rows(selected)
        reference = score_rows([baseline[row["listing_id"]] for row in selected])
        results[family] = {"candidate": metric, "baseline": reference}
        checks.append({"check": family + ": sufficient rows", "passed": len(selected) >= minimum,
                       "actual": len(selected), "limit": minimum})
        if not selected:
            continue
        cap = limits["overall_mae_pkr"] if family == "overall" else limits["family_mae_pkr"][family]
        checks.extend([
            {"check": family + ": MAE PKR", "passed": metric["mae_pkr"] <= cap, "actual": metric["mae_pkr"], "limit": cap},
            {"check": family + ": median percentage error", "passed": metric["median_ape_pct"] <= limits["median_ape_pct"],
             "actual": metric["median_ape_pct"], "limit": limits["median_ape_pct"]},
            {"check": family + ": positive predictions", "passed": metric["nonpositive_predictions"] == 0,
             "actual": metric["nonpositive_predictions"], "limit": 0},
        ])
        improvement = 100 * (reference["mae_pkr"] - metric["mae_pkr"]) / reference["mae_pkr"] if reference["mae_pkr"] else None
        required = limits["minimum_baseline_improvement_pct"] if family == "overall" else 0
        results[family]["baseline_improvement_pct"] = improvement
        checks.append({"check": family + ": baseline improvement", "passed": improvement is not None and improvement >= required,
                       "actual": improvement, "limit": required})
    return {"passed": all(row["passed"] for row in checks), "metrics": results, "checks": checks}


def evidence_rows(root, name, data):
    rows = [row for row in read_csv(root / "predictions.csv") if row["experiment"] == name]
    by_id = {row["listing_id"]: row for row in rows}
    if len(rows) != len(data.listing_ids) or set(by_id) != set(data.listing_ids):
        raise ValueError("Development evidence does not have the exact current membership")
    for index, listing_id in enumerate(data.listing_ids):
        row = by_id[listing_id]
        if float(row["actual_pkr"]) != data.targets[index] or int(row["fold"]) != data.validation_folds[index] or row["group_id"] != data.group_ids[index]:
            raise ValueError("Development evidence has changed targets, folds, or groups")
    return by_id


def read_policy(path):
    policy = read_json(path)
    if policy.get("version") != 1 or policy.get("model") != "catboost" or policy.get("input_contract_id") != "cars_reduced_v1":
        raise ValueError("Use the declared CatBoost nine-input pilot qualification policy")
    if policy["coverage"]["required_folds"] != 3:
        raise ValueError("Pilot support requires all three development folds")
    counts = list(policy["coverage"].values()) + [policy[key] for key in (
        "development_min_supported_family_groups", "test_min_supported_rows", "test_min_supported_family_rows")]
    if any(type(value) is not int or value < 1 for value in counts):
        raise ValueError("Coverage and evaluation counts must be positive integers")
    limits = policy["errors"]
    values = [limits["overall_mae_pkr"], limits["median_ape_pct"], *limits["family_mae_pkr"].values()]
    if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("Error limits must be positive finite values")
    if not 0 <= limits["minimum_baseline_improvement_pct"] <= 100:
        raise ValueError("Baseline improvement limit must be between zero and 100 percent")
    return policy


def qualify_demo(dataset, evaluation, evidence, baseline, output, policy_path, *, usage_dir=None):
    sources = [dataset, evaluation, evidence, baseline]
    output = output_path(output, sources)
    policy = read_policy(policy_path)
    evaluation_manifest = verify_artifact(evaluation)
    if usage_path(evaluation_manifest["split_id"], usage_dir).exists():
        raise ValueError("This reserved test has already been opened; do not redefine support against its outcomes")
    contract = load_predictor_contract()
    model_settings = {"seed": policy["seed"], "target": "raw_pkr", "candidates": {policy["model"]: policy["parameters"]}}
    for root in (evidence, baseline):
        verify_reference(root.resolve(), dataset.resolve(), evaluation.resolve(), model_settings)
    details = read_json(evidence / "fold_details.json")
    selected = [row for row in details if row["experiment"] == policy["experiment"]]
    if len(selected) != 3 or any(row["input_columns"] != contract["columns"] for row in selected):
        raise ValueError("Candidate evidence must use the adopted nine columns in all three folds")
    paths = [policy_path, DEFAULT_CONTRACT] + [path for root in sources for path in root.iterdir() if path.is_file()]
    fingerprints = input_hashes(paths)
    data = load_predictor_development(dataset, evaluation, contract=contract)
    candidate = evidence_rows(evidence, policy["experiment"], data)
    reference = evidence_rows(baseline, policy["baseline_experiment"], data)
    support = build_support(data, policy)
    return freeze_qualification(output, dataset, evaluation, data, candidate, reference, support, policy,
                                contract, fingerprints, evaluation_manifest["split_id"])


def freeze_qualification(output, dataset, evaluation, data, candidate, reference, support, policy, contract, fingerprints, split_id):
    coverage, supported = [], []
    for index, row in enumerate(data.inputs):
        reason = support_reason(row, support)
        listing_id = data.listing_ids[index]
        coverage.append({"listing_id": listing_id, "family": family_name(row), "variant": row["variant"],
                         "year": row["year"], "supported": reason is None, "reason": reason or ""})
        if reason is None:
            supported.append(candidate[listing_id])
    report = error_report(supported, reference, policy, 1, 1)
    for family in policy["errors"]["family_mae_pkr"]:
        indices = [i for i, row in enumerate(data.inputs) if family_name(row) == family and coverage[i]["supported"]]
        count = len({data.group_ids[i] for i in indices})
        report["checks"].append({"check": family + ": supported development groups", "actual": count,
                                 "limit": policy["development_min_supported_family_groups"],
                                 "passed": count >= policy["development_min_supported_family_groups"]})
    report["passed"] = all(check["passed"] for check in report["checks"])
    report["full_development_metrics"] = score_rows(list(candidate.values()))
    verify_inputs({"input_sha256": fingerprints})
    output.mkdir(parents=True)
    for name in ("catalogue.json", "scope.json"):
        (output / name).write_bytes((evaluation / name).read_bytes())
    for name, value in {"candidate.json": policy, "contract.json": contract,
                        "support.json": support, "development_metrics.json": report}.items():
        save_json(output / name, value)
    save_csv(output / "coverage.csv", coverage)
    lines = ["# Frozen demo qualification", "", f"Candidate: `{policy['candidate_id']}`. Development gate passed: {report['passed']}.",
             f"Development rows: {len(data.targets)}. Supported rows: {len(supported)}. Supported variants: {len(support['entries'])}.", "",
             "Support uses development attributes/groups only: five independent variant examples in all three folds, "
             "well-covered family-years/cities, observed variant years/cities/mileage and transmission/displacement/assembly combinations.",
             "Limits are pilot operational choices informed by development errors, not market reliability guarantees. "
             "Supported-subset errors are post-selection development evidence, not nested validation.", "",
             "| Family | Rows | MAE PKR | Median percentage error | Baseline improvement |", "|---|---:|---:|---:|---:|"]
    for family, values in report["metrics"].items():
        metric = values["candidate"]
        if metric:
            improvement = values.get("baseline_improvement_pct")
            text = "n/a" if improvement is None else f"{improvement:.1f}%"
            lines.append(f"| {family} | {metric['count']} | {metric['mae_pkr']:,.0f} | {metric['median_ape_pct']:.2f}% | {text} |")
    lines += ["", "The test remains reserved. Candidate, features, support rules and limits must not change after test outcomes are opened.", ""]
    (output / "qualification.md").write_text("\n".join(lines), encoding="utf-8")
    return finish_artifact(output, {"kind": "demo_qualification", "candidate_id": policy["candidate_id"],
                           "status": "qualified_development" if report["passed"] else "failed_development",
                           "dataset_id": read_json(dataset / "manifest.json")["dataset_id"], "split_id": split_id,
                           "development_rows": len(data.targets), "supported_development_rows": len(supported),
                           "test_status": "reserved_unopened_for_model_outcomes"}, fingerprints,
                          ("pilot/qualification.py", "pilot/support.py", "pilot/predictor_inputs.py"))
