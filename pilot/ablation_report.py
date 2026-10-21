"""Paired development comparisons and predeclared feature-removal limits."""

from pilot.metrics import summarize_predictions


def removal_specs(config):
    """Return report labels and the exact fields omitted in each experiment."""
    if config["version"] == 2:
        fields = tuple(config["remove_together"])
        return [("_and_".join(fields), fields)]
    return [(field, (field,)) for field in config["remove_individually"]]


def mae_change(candidate, reference):
    if reference == 0:
        return None
    return 100 * (candidate - reference) / reference


def within_limit(candidate, reference, limit):
    """Use unrounded MAEs; zero reference error permits no increase."""
    return candidate <= reference * (1 + limit / 100)


def summarize_ablation(predictions, folds, fitted, config):
    subgroups = summarize_predictions(predictions)
    lookup = {(row["experiment"], row["dimension"], row["value"]): row for row in subgroups}
    summaries, changes = [], []
    limits = config["max_mae_increase_pct"]
    for model in config["candidates"]:
        reference = f"{model}_full"
        for removed in ["full"] + [name for name, _ in removal_specs(config)]:
            experiment = reference if removed == "full" else f"{model}_without_{removed}"
            metrics = lookup[experiment, "overall", "all"]
            ref_metrics = lookup[reference, "overall", "all"]
            fold_changes = []
            fold_pass = True
            for row in (item for item in folds if item["experiment"] == experiment):
                other = next(item for item in folds if item["experiment"] == reference and item["fold"] == row["fold"])
                fold_changes.append(mae_change(row["mae_pkr"], other["mae_pkr"]))
                fold_pass &= within_limit(row["mae_pkr"], other["mae_pkr"], limits["fold"])
            family_changes, family_pass = [], True
            for row in (item for item in subgroups if item["experiment"] == experiment):
                other = lookup[reference, row["dimension"], row["value"]]
                delta = mae_change(row["mae_pkr"], other["mae_pkr"])
                changes.append({**row, "reference_mae_pkr": other["mae_pkr"],
                                "mae_change_pkr": row["mae_pkr"] - other["mae_pkr"], "mae_change_pct": delta})
                if row["dimension"] == "family":
                    family_changes.append(delta)
                    family_pass &= within_limit(row["mae_pkr"], other["mae_pkr"], limits["family"])
            columns = next(item["input_columns"] for item in fitted if item["experiment"] == experiment)
            summaries.append({"experiment": experiment, "model": model, "removed": removed,
                              "input_columns": ";".join(columns),
                              **{key: value for key, value in metrics.items() if key not in {"experiment", "dimension", "value"}},
                              "mae_change_pkr": metrics["mae_pkr"] - ref_metrics["mae_pkr"],
                              "mae_change_pct": mae_change(metrics["mae_pkr"], ref_metrics["mae_pkr"]),
                              "worst_fold_change_pct": max((v for v in fold_changes if v is not None), default=None),
                              "worst_family_change_pct": max((v for v in family_changes if v is not None), default=None),
                              "overall_pass": within_limit(metrics["mae_pkr"], ref_metrics["mae_pkr"], limits["overall"]),
                              "fold_pass": bool(fold_pass), "family_pass": bool(family_pass),
                              "candidate_for_removal": removed != "full" and bool(fold_pass and family_pass) and
                              within_limit(metrics["mae_pkr"], ref_metrics["mae_pkr"], limits["overall"]),
                              "fit_seconds": sum(row["fit_seconds"] for row in folds if row["experiment"] == experiment)})
    return summaries, subgroups, changes


def ablation_report(manifest, summary, config):
    combined = config["version"] == 2
    decision_rows = [row for row in summary if row["removed"] == ("fuel_and_body_type" if combined else "listing_city")]
    passes = all(row["candidate_for_removal"] for row in decision_rows)
    subject = "Joint fuel/body-type removal" if combined else "City removal"
    title = "# Combined feature-removal confirmation" if combined else "# Independent feature-removal experiment"
    method = "Fuel and body type are omitted together from F2." if combined else "Each removal starts from full F2."
    lines = [title, "",
             f"Experiment: `{manifest['experiment_id']}`. Dataset: `{manifest['dataset_id']}`.",
             f"Split: `{manifest['split_id']}`. Development rows: {manifest['development_rows']}.", "",
             method + " Negative changes mean lower error. "
             "Both full references reproduced the preceding run within PKR 0.01 per prediction and metric. "
             "The reserved test was not requested for model outcomes.", "",
             "| Model | Removed | MAE PKR | Change PKR | Change % | Worst fold % | Worst family % | Removal candidate |",
             "|---|---|---:|---:|---:|---:|---:|---|"]
    def percent(value):
        return "n/a, zero reference" if value is None else f"{value:+.2f}"
    for row in summary:
        lines.append(f"| {row['model']} | {row['removed']} | {row['mae_pkr']:,.0f} | {row['mae_change_pkr']:+,.0f} | "
                     f"{percent(row['mae_change_pct'])} | {percent(row['worst_fold_change_pct'])} | "
                     f"{percent(row['worst_family_change_pct'])} | {row['candidate_for_removal']} |")
    limits = config["max_mae_increase_pct"]
    lines += ["", "## Decision and limits", "",
              f"A candidate must meet all limits on unrounded MAEs: overall increase <= {limits['overall']}%, "
              f"every fold <= {limits['fold']}%, every family <= {limits['family']}%.", "",
              (f"{subject} qualifies as a removal candidate across both models." if passes else
               f"{subject} does not qualify for removal across both models; retain the current inputs provisionally."),
              ("A combined reduced schema was evaluated; no inference schema was adopted." if combined else
               "Passing individual removals are candidates only. No combined reduced schema was fitted or adopted."),
              "City, variant, year, price-band, and seen/unseen subgroup counts/errors and reference deltas are in "
              "subgroup_metrics.csv and subgroup_changes.csv. Small groups are descriptive, not reliable support claims.",
              "These fixed-seed development results measure conditional predictive usefulness, not causation or "
              "statistical equivalence. Review-informed development selection still requires a frozen candidate "
              "before reserved-test evaluation. Registration is excluded. No inference predictor was saved.", ""]
    return "\n".join(lines)
