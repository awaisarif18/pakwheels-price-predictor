"""Readable development comparison report, with no final-test conclusions."""


def comparison_report(manifest: dict, results: list[dict], subgroups: list[dict], predictions: list[dict]) -> str:
    ranked = sorted(results, key=lambda row: row["mae_pkr"])
    best = ranked[0]
    baseline = next(row for row in results if row["experiment"] == "median_F0")
    lines = [
        "# Exploratory model comparison", "",
        f"Experiment: `{manifest['experiment_id']}`. Dataset: `{manifest['dataset_id']}`.",
        f"Split: `{manifest['split_id']}`. Development rows: {manifest['development_rows']}.", "",
        "Each row receives one prediction from a model fitted on the other development folds. "
        "All candidates use identical membership. The reserved demo test was not requested or scored.", "",
        "## Development results", "",
        "| Candidate | MAE PKR | Median error PKR | Median percentage error | Fold MAE min / max PKR | Improvement over median | Folds better than median | Fit seconds |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ranked:
        improvement = row["baseline_improvement_pct"]
        improvement_text = "n/a, baseline error is zero" if improvement is None else f"{improvement:.1f}%"
        lines.append(
            f"| {row['experiment']} | {row['mae_pkr']:,.0f} | {row['median_ae_pkr']:,.0f} | "
            f"{row['median_ape_pct']:.1f}% | {row['fold_mae_min_pkr']:,.0f} / {row['fold_mae_max_pkr']:,.0f} | "
            f"{improvement_text} | {row['folds_better_than_baseline']} | {row['fit_seconds']:.3f} |"
        )
    lines += [
        "", f"The lowest observed pooled development MAE is `{best['experiment']}`. "
        "This is an exploratory ranking, not a frozen demo candidate or a reliable market error estimate.", "",
        "## Family errors for the lowest-MAE candidate", "",
        "| Family | Rows | Candidate MAE PKR | Median baseline MAE PKR |",
        "|---|---:|---:|---:|",
    ]
    for row in subgroups:
        if row["experiment"] == best["experiment"] and row["dimension"] == "family":
            other = next(item for item in subgroups if item["experiment"] == baseline["experiment"]
                         and item["dimension"] == "family" and item["value"] == row["value"])
            lines.append(f"| {row['value']} | {row['count']} | {row['mae_pkr']:,.0f} | {other['mae_pkr']:,.0f} |")
    lines += [
        "", "## Largest held-out errors for the lowest-MAE candidate", "",
        "IDs refer to private saved source evidence. Review causes separately; a large error alone does not prove a bad label.", "",
        "| Listing ID | Family | Year | Actual PKR | Predicted PKR | Absolute error PKR | Unseen variant | Unseen city |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    largest = sorted((row for row in predictions if row["experiment"] == best["experiment"]),
                     key=lambda row: row["absolute_error_pkr"], reverse=True)[:10]
    for row in largest:
        lines.append(f"| {row['listing_id']} | {row['family']} | {row['year']} | {row['actual_pkr']:,.0f} | "
                     f"{row['predicted_pkr']:,.0f} | {row['absolute_error_pkr']:,.0f} | {row['unseen_variant']} | {row['unseen_city']} |")
    lines += [
        "", "## Scope and interpretation", "",
        "One fixed configuration per algorithm; raw-PKR targets only. No hyperparameter search, target clipping, "
        "log transform, or early stopping. Median uses family/year, family, make, then global training medians "
        "with the configured minimum support. Its predictions intentionally match across F0-F2.",
        "F0 uses family/year/mileage/city; F1 adds variant; F2 adds fuel/transmission/displacement/assembly/body type. "
        "The same deterministic input contract is used for every fold. Fitted encoders, imputers, scalers, "
        "medians, and CatBoost categorical statistics learn only from each training fold.",
        "Sparse variants and cities, source-evidence retention, marketplace ordering, and a single collection period "
        "limit generalization. Reported subgroup counts are descriptive; tiny groups cannot establish reliability. "
        "Family/variant/year/city/price-band errors and seen/unseen errors are in subgroup_metrics.csv.",
        "Predictions are not clipped. Nonpositive prediction counts are recorded and would block demo qualification. "
        "No predictor is saved or declared supported in this comparison.",
        "Next: inspect large validation misses and coverage, then prepare deeper scoped collection. "
        "Keep the reserved test closed until support, preprocessing, and candidate choices are frozen.", "",
    ]
    return "\n".join(lines)
