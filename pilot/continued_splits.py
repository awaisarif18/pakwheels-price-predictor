"""Extend frozen development/test history when a larger dataset arrives."""

from collections import defaultdict
import hashlib

from pilot.splits import build_splits, validate_splits


def build_continued_splits(rows: list[dict], config: dict) -> dict:
    """Reserve new groups only among new history; preserve earlier partitions.

    Prior development groups never become untouched tests. Prior test groups
    never enter training. Combined possible-repost groups use one old fold;
    development/test collisions must already have been quarantined.
    """
    new = [row for row in rows if row["historical_partition"] == "new"]
    new_policy = config.get("new_group_policy", "reserve_by_family")
    if new_policy not in {"reserve_by_family", "development_only"}:
        raise ValueError("Unknown new-group evaluation policy")
    if new_policy == "development_only":
        if type(config["seed"]) is not int or type(config["development_folds"]) is not int or config["development_folds"] < 2:
            raise ValueError("Reviewed evaluation requires an integer seed and at least two folds")
        result = {"split_schema_version": 1, "seed": config["seed"], "test_fraction": config["test_fraction"],
                  "development_folds": config["development_folds"], "stratification": "make/model family",
                  "status": "exploratory_reviewed_rebuild", "test_status": "reserved_unopened", "assignments": []}
    else:
        result = build_splits(new, config)
    assignments = result["assignments"]
    old_groups = defaultdict(list)
    for row in rows:
        if row["historical_partition"] != "new":
            old_groups[row["group_id"]].append(row)
    for group_id, group in old_groups.items():
        locations = set()
        for row in group:
            partition, fold = row["historical_partition"], row["historical_validation_fold"]
            if partition == "development" and isinstance(fold, str) and fold.isdigit():
                fold = int(fold)
            if partition == "demo_test" and fold == "":
                fold = None
            locations.add((partition, fold))
        if len(locations) != 1:
            raise ValueError("Conflicting historical locations in one group")
        partition, fold = next(iter(locations))
        if partition not in {"development", "demo_test"}:
            raise ValueError("Quarantined history cannot enter evaluation")
        assignments.extend({"listing_id": row["listing_id"], "group_id": group_id,
                            "partition": partition, "validation_fold": fold} for row in group)
    if new_policy == "development_only":
        _add_reviewed_development(rows, new, assignments, config)
    result["assignments"] = sorted(assignments, key=lambda item: item["listing_id"])
    result["history_policy"] = ("Preserve earlier partitions; add reviewed reinstatements only to development; quarantine collisions"
                                if new_policy == "development_only" else
                                "Preserve earlier partitions; reserve 20% of new groups by family; quarantine development/test collisions")
    validate_splits(rows, result)
    return result


def _add_reviewed_development(rows, new, assignments, config):
    """Balance reinstated groups without changing an existing holdout or fold."""
    folds = config["development_folds"]
    by_id = {row["listing_id"]: row for row in rows}
    family_counts = defaultdict(lambda: [0] * folds)
    global_counts = [0] * folds
    for item in assignments:
        if item["partition"] == "development":
            row = by_id[item["listing_id"]]
            family_counts[(row["make"], row["model"])][item["validation_fold"]] += 1
            global_counts[item["validation_fold"]] += 1
    groups = defaultdict(list)
    for row in new:
        groups[row["group_id"]].append(row)
    def rank(group_id):
        return -len(groups[group_id]), hashlib.sha256(f"{config['seed']}:reviewed-development:{group_id}".encode()).hexdigest()
    for group_id in sorted(groups, key=rank):
        group = groups[group_id]
        family = (group[0]["make"], group[0]["model"])
        fold = min(range(folds), key=lambda index: (family_counts[family][index], global_counts[index], index))
        assignments.extend({"listing_id": row["listing_id"], "group_id": group_id, "partition": "development",
                            "validation_fold": fold} for row in group)
        family_counts[family][fold] += len(group)
        global_counts[fold] += len(group)
