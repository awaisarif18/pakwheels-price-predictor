"""Resolve names conservatively against the observed pilot catalogue."""

import json
from pathlib import Path

MISSING_LABELS = {"", "n/a", "na", "unknown", "none", "null", "-", "not available"}


def label(value) -> str | None:
    text = " ".join(str(value).split()) if value is not None else ""
    return None if text.casefold() in MISSING_LABELS else text


def load_catalogue(path: Path) -> dict:
    catalogue = json.loads(path.read_text(encoding="utf-8"))
    if catalogue.get("catalogue_version") != 1:
        raise ValueError("Unsupported identity catalogue version")
    return catalogue


def resolve_identity(row: dict, catalogue: dict) -> dict:
    """Preserve unknown variants; never substitute base trim or another family."""
    make, model, variant = (label(row.get(field)) for field in ["make", "model", "variant"])
    family = next((item for item in catalogue["families"] if make and model and make.casefold() == item["make"].casefold() and model.casefold() == item["model"].casefold()), None)
    if family is None:
        return {"make": make, "model": model, "variant": variant, "identity_status": "outside_catalogue" if make and model else "unresolved_family"}
    if variant is None:
        return {"make": family["make"], "model": family["model"], "variant": None, "identity_status": "family_known_variant_unspecified"}
    canonical = next((value for value in family["variants"] if value.casefold() == variant.casefold()), None)
    return {"make": family["make"], "model": family["model"], "variant": canonical or variant, "identity_status": "observed_label_resolved" if canonical else "unresolved_variant"}
