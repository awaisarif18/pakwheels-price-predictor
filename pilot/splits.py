"""Deterministic family-stratified group assignments, independent of targets."""

import hashlib
import math
from collections import Counter, defaultdict


def _groups(rows: list[dict]) -> dict:
    groups, seen = {}, set()
    for row in rows:
        listing_id, group_id = str(row.get("listing_id", "")).strip(), str(row.get("group_id", "")).strip()
        family = (row.get("make"), row.get("model"))
        if not listing_id or not group_id or not all(family):
            raise ValueError("Every row requires listing_id, group_id, make, and model")
        if listing_id in seen:
            raise ValueError(f"Duplicate listing ID: {listing_id}")
        seen.add(listing_id)
        group = groups.setdefault(group_id, {"family": family, "ids": []})
        if group["family"] != family:
            raise ValueError(f"Cross-family group requires review: {group_id}")
        group["ids"].append(listing_id)
    if not groups:
        raise ValueError("Cannot split an empty population")
    return groups


def build_splits(rows: list[dict], config: dict) -> dict:
    """Reserve test groups first, then assign development validation folds.

    Uses only identities, group IDs, and row counts, never target/feature values.
    Stable across input ordering and Python random-library versions. Requires
    each family to have at least one test group and one group in every fold.
    """
    seed, fraction, folds = config["seed"], config["test_fraction"], config["development_folds"]
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(folds, bool) or not isinstance(folds, int) or folds < 2:
        raise ValueError("development_folds must be an integer >= 2")
    if isinstance(fraction, bool) or not isinstance(fraction, (int, float)) or not 0 < fraction < 1:
        raise ValueError("test_fraction must be between zero and one")
    groups = _groups(rows)
    families = defaultdict(list)
    for group_id, group in groups.items():
        families[group["family"]].append(group_id)

    def rank(group_id: str, phase: str) -> tuple:
        digest = hashlib.sha256(f"{seed}:{phase}:{group_id}".encode()).hexdigest()
        return digest, group_id

    memberships = {}
    global_fold_rows = [0] * folds
    for family, members in sorted(families.items()):
        ordered = sorted(members, key=lambda group_id: rank(group_id, "test"))
        test_count = max(1, math.floor(len(ordered) * fraction + 0.5))
        if len(ordered) - test_count < folds:
            raise ValueError(f"Too few independent groups for family {family}: {len(ordered)}")
        for group_id in ordered[:test_count]:
            memberships[group_id] = ("demo_test", None)
        development = sorted(ordered[test_count:], key=lambda group_id: (-len(groups[group_id]["ids"]), rank(group_id, "development")))
        family_fold_rows, family_fold_groups = [0] * folds, [0] * folds
        for group_id in development:
            # Empty folds receive a group before any fold receives a second one.
            fold = min(range(folds), key=lambda index: (family_fold_groups[index] > 0, family_fold_rows[index], global_fold_rows[index], index))
            memberships[group_id] = ("development", fold)
            size = len(groups[group_id]["ids"])
            family_fold_rows[fold] += size
            global_fold_rows[fold] += size
            family_fold_groups[fold] += 1
    assignments = [
        {"listing_id": listing_id, "group_id": group_id, "partition": memberships[group_id][0],
         "validation_fold": memberships[group_id][1]}
        for group_id, group in groups.items() for listing_id in group["ids"]
    ]
    result = {
        "split_schema_version": 1, "seed": seed, "test_fraction": fraction,
        "development_folds": folds, "stratification": "make/model family",
        "status": "exploratory_small_sample", "test_status": "reserved_unopened",
        "assignments": sorted(assignments, key=lambda item: item["listing_id"]),
    }
    validate_splits(rows, result)
    return result


def validate_splits(rows: list[dict], splits: dict) -> None:
    """Reject omissions, overlaps, changed groups, and malformed saved assignments."""
    if splits.get("split_schema_version") != 1:
        raise ValueError("Unsupported split schema")
    groups = _groups(rows)
    expected = {listing_id: group_id for group_id, group in groups.items() for listing_id in group["ids"]}
    folds = splits["development_folds"]
    if isinstance(folds, bool) or not isinstance(folds, int) or folds < 2:
        raise ValueError("Invalid development fold count")
    seen, membership = set(), {}
    family_partitions = defaultdict(set)
    for item in splits["assignments"]:
        listing_id, group_id = item["listing_id"], item["group_id"]
        if listing_id in seen or expected.get(listing_id) != group_id:
            raise ValueError("Split contains duplicate, unknown, or regrouped listing IDs")
        seen.add(listing_id)
        partition, fold = item["partition"], item["validation_fold"]
        if partition == "demo_test":
            if fold is not None:
                raise ValueError("Demo test cannot belong to a validation fold")
        elif partition == "development":
            if isinstance(fold, bool) or not isinstance(fold, int) or not 0 <= fold < folds:
                raise ValueError("Invalid validation fold")
        else:
            raise ValueError("Unknown evaluation partition")
        location = (partition, fold)
        if group_id in membership and membership[group_id] != location:
            raise ValueError("Group leakage across evaluation partitions or folds")
        membership[group_id] = location
        family_partitions[groups[group_id]["family"]].add(location)
    if seen != set(expected):
        raise ValueError("Split omits dataset rows")
    required = {("demo_test", None)} | {("development", fold) for fold in range(folds)}
    if any(locations != required for locations in family_partitions.values()):
        raise ValueError("Every family requires test groups and all development folds")


def split_counts(rows: list[dict], splits: dict) -> list[dict]:
    """Counts only, suitable for reports without inspecting test errors."""
    validate_splits(rows, splits)
    families = {row["listing_id"]: f"{row['make']} {row['model']}" for row in rows}
    counts = Counter()
    group_counts = defaultdict(set)
    for item in splits["assignments"]:
        key = (families[item["listing_id"]], item["partition"], item["validation_fold"])
        counts[key] += 1
        group_counts[key].add(item["group_id"])
    return [
        {"family": family, "partition": partition, "validation_fold": fold,
         "rows": count, "groups": len(group_counts[(family, partition, fold)])}
        for (family, partition, fold), count in sorted(counts.items())
    ]
