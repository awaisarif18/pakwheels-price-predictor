"""Consolidate observations without losing identity or evaluation history."""

from collections import defaultdict
from datetime import datetime
import hashlib
import json

SPEC_FIELDS = ("make", "model", "variant", "year", "mileage_km", "engine_cc",
               "fuel", "transmission", "listing_city", "assembly")


def consolidate_observations(observations: list[dict], parent_assignments: list[dict]):
    """Group all historical specs and IDs, then retain the latest observation.

    Specification matches are conservative split groups, not proven duplicates.
    Link older specs before selecting latest rows so changing mileage cannot
    disconnect a known listing from its earlier possible-repost group.
    """
    parents = {row["listing_id"]: row["listing_id"] for row in observations}

    def find(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    def union(first, second):
        a, b = find(first), find(second)
        parents[max(a, b)] = min(a, b)

    specs, historical_groups = {}, {}
    for row in observations:
        values = tuple(row.get(field) for field in SPEC_FIELDS)
        if all(value is not None for value in values):
            union(row["listing_id"], specs.setdefault(values, row["listing_id"]))
    for assignment in parent_assignments:
        listing_id = assignment["listing_id"]
        if listing_id in parents:
            previous = historical_groups.setdefault(assignment["group_id"], listing_id)
            union(listing_id, previous)
    members, by_id = defaultdict(list), defaultdict(list)
    for row in observations:
        by_id[row["listing_id"]].append(row)
    for listing_id in by_id:
        members[find(listing_id)].append(listing_id)
    history = {item["listing_id"]: item for item in parent_assignments}
    selected, decisions = [], []
    for identifiers in sorted(members.values(), key=min):
        assignments = [history[key] for key in identifiers if key in history]
        partitions = {item["partition"] for item in assignments}
        conflict = len(partitions) > 1
        partition = next(iter(partitions)) if len(partitions) == 1 else "new"
        folds = [item["validation_fold"] for item in assignments if item["partition"] == "development"]
        group_id = ("listing_" + identifiers[0] if len(identifiers) == 1 else
                    "linked_" + hashlib.sha256(json.dumps(sorted(identifiers)).encode()).hexdigest()[:12])
        for listing_id in sorted(identifiers):
            versions = by_id[listing_id]
            row = _latest(versions)
            identity_conflict = len({(item["make"], item["model"]) for item in versions}) > 1
            reasons = [reason for reason in row["exclusion_reasons"].split(";") if reason]
            if conflict:
                reasons.append("historical_development_test_group_conflict")
            if identity_conflict:
                reasons.append("cross_batch_family_conflict")
            row.update(group_id=group_id, historical_partition="quarantined" if conflict else partition,
                       historical_validation_fold=min(folds) if folds and not conflict else None,
                       observation_count=len(versions), observation_batches=";".join(sorted({item["source_batch"] for item in versions})),
                       exclusion_reasons=";".join(sorted(set(reasons))))
            row["modeling_candidate"] = row["modeling_candidate"] and not reasons
            row["source_checked_candidate"] = row["source_checked_candidate"] and not reasons
            selected.append(row)
            decisions.append({"listing_id": listing_id, "selected_batch": row["source_batch"],
                              "selected_collected_at": row["collected_at"], "observations": len(versions),
                              "group_id": group_id, "historical_partition": row["historical_partition"],
                              "exclusion_reasons": row["exclusion_reasons"]})
    return sorted(selected, key=lambda row: row["listing_id"]), decisions


def _latest(versions):
    def timestamp(row):
        value = datetime.fromisoformat(row["collected_at"])
        if value.tzinfo is None:
            raise ValueError("Observation timestamps require an explicit timezone")
        return value
    newest = max(timestamp(row) for row in versions)
    tied = [row for row in versions if timestamp(row) == newest]
    if len(tied) > 1:
        fields = (*SPEC_FIELDS, "price_pkr", "source_checked_candidate")
        if len({tuple(row.get(field) for field in fields) for row in tied}) > 1:
            raise ValueError("Conflicting observations share a collection timestamp")
    return dict(min(tied, key=lambda row: row["source_batch"]))
