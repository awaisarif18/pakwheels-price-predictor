"""Deterministic candidate selection; no fitted preprocessing or model training."""

import hashlib
import json
from collections import defaultdict

from pilot.evidence import whole_number
from pilot.identity import label, resolve_identity


def prepare_rows(rows: tuple[dict, ...], catalogue: dict, scope: dict, evidence: dict) -> list[dict]:
    """Normalize a copy and expose exclusions, uncertainty, and source updates."""
    prepared = []
    allowed = {(item["make"], item["model"]) for item in scope["candidate_families"]}
    for original in rows:
        row = {field: str(value).strip() if value is not None and str(value).strip() else None for field, value in original.items()}
        # A metadata value such as registration meaning "unknown" is meaningful.
        for field in ["make", "model", "variant", "fuel", "transmission", "assembly", "body_type", "listing_city"]:
            row[field] = label(row.get(field))
        review = evidence.get(original["listing_id"], {})
        changes = review.get("updates", {})
        row.update(changes)
        row.update(resolve_identity(row, catalogue))
        notes, exclusions = [], []
        for field in ["year", "price_pkr", "mileage_km", "engine_cc", "registration_year"]:
            value = row.get(field)
            row[field] = whole_number(value)
            if value is not None and row[field] is None:
                (exclusions if field in {"year", "price_pkr", "mileage_km"} else notes).append(f"invalid_number:{field}")
        for field, positive in [("price_pkr", True), ("mileage_km", False), ("year", True)]:
            value = row.get(field)
            if value is None or (value <= 0 if positive else value < 0):
                exclusions.append(f"missing_or_invalid:{field}")
        if (row.get("make"), row.get("model")) not in allowed:
            exclusions.append("outside_candidate_families")
        if row["year"] is not None and not scope["year_range"][0] <= row["year"] <= scope["year_range"][1]:
            exclusions.append("outside_candidate_year_range")
        if row["identity_status"] == "unresolved_variant":
            exclusions.append("unresolved_variant")
        if row.get("variant") is None:
            notes.append("variant_unspecified_not_base_trim")
        for field in ["fuel", "transmission", "assembly", "body_type"]:
            if row.get(field):
                row[field] = row[field].upper() if row[field].upper() in {"CNG", "LPG", "PHEV", "CVT", "SUV"} else row[field].title()
        if row.get("engine_cc") is not None and row["engine_cc"] <= 0:
            notes.append("invalid_engine_displacement")
            row["engine_cc"] = None
        if row.get("registration_year") is not None:
            if row.get("registration_year_meaning") == "unknown":
                notes.append("registration_meaning_unknown")
            if row.get("year") and row["registration_year"] < row["year"]:
                notes.append("registration_precedes_model_year")
        notes.extend(review.get("flags", []))
        if any(note.startswith("unresolved_source_disagreement:") for note in notes):
            exclusions.append("unresolved_source_disagreement")
        price_verified = bool(review.get("price_verified"))
        if not price_verified:
            notes.append("asking_price_not_verified_against_cached_main_price_box")
        row.update(
            source_price_verified=price_verified, evidence_available=bool(review),
            source_updates=json.dumps(changes, sort_keys=True), quality_notes=";".join(notes),
            exclusion_reasons=";".join(sorted(set(exclusions))),
            modeling_candidate=not exclusions, source_checked_candidate=not exclusions and price_verified,
            group_id=f"listing_{original['listing_id']}",
        )
        prepared.append(row)
    # Conservative split groups for identical vehicle specifications, not deletions.
    fingerprints = defaultdict(list)
    fields = ["make", "model", "variant", "year", "mileage_km", "engine_cc", "fuel", "transmission", "listing_city", "assembly"]
    for row in prepared:
        values = tuple(row.get(field) for field in fields)
        if all(value is not None for value in values):
            fingerprints[values].append(row)
    for values, members in fingerprints.items():
        if len(members) > 1:
            group = "suspected_" + hashlib.sha256(json.dumps(values).encode()).hexdigest()[:12]
            for row in members:
                row["group_id"] = group
                row["quality_notes"] += ";identical_specifications_possible_repost_not_proven"
    return prepared
