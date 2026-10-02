"""Shared, unfitted input preparation for training and future prediction."""

from collections.abc import Mapping

from pilot.evidence import whole_number
from pilot.identity import label, resolve_identity

FEATURE_SCHEMA_VERSION = 1
MISSING_CATEGORY = "__MISSING__"
FEATURE_SETS = {
    "F0": ("make", "model", "year", "mileage_km", "listing_city"),
    "F1": ("make", "model", "year", "mileage_km", "listing_city", "variant"),
    "F2": ("make", "model", "year", "mileage_km", "listing_city", "variant",
           "fuel", "transmission", "engine_cc", "assembly", "body_type"),
}
NUMERICAL_FIELDS = {"year", "mileage_km", "engine_cc"}


def _integer(value, field: str, minimum: int, optional: bool = False) -> int | None:
    if optional and label(value) is None:
        return None
    number = None if isinstance(value, bool) else whole_number(value)
    if number is None or number < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return number


def prepare_input(row: Mapping, feature_set: str, catalogue: dict, scope: dict) -> dict:
    """Return ordered model inputs without learning from a dataset or reading price.

    Accept the same named fields from a prepared CSV or a future prediction form.
    Reject unknown families/variants and invalid required values. Missing optional
    categories use a fixed token; optional displacement remains None. These rules
    describe input semantics, not evaluated predictor support.
    """
    if feature_set not in FEATURE_SETS:
        raise ValueError(f"Unknown feature set: {feature_set}")
    identity = resolve_identity(row, catalogue)
    allowed = {(item["make"], item["model"]) for item in scope["candidate_families"]}
    if (identity["make"], identity["model"]) not in allowed:
        raise ValueError("Family is outside the candidate scope")
    if identity["identity_status"] == "unresolved_variant":
        raise ValueError("Variant is not resolved by the catalogue")
    year = _integer(row.get("year"), "year", 1)
    if not scope["year_range"][0] <= year <= scope["year_range"][1]:
        raise ValueError("Model year is outside the candidate scope")
    city = label(row.get("listing_city"))
    if city is None:
        raise ValueError("listing_city is required")
    values = {
        "make": identity["make"], "model": identity["model"], "year": year,
        "mileage_km": _integer(row.get("mileage_km"), "mileage_km", 0),
        "listing_city": city.title(), "variant": identity["variant"] or MISSING_CATEGORY,
    }
    if feature_set == "F2":
        values["engine_cc"] = _integer(row.get("engine_cc"), "engine_cc", 1, optional=True)
        for field in ("fuel", "transmission", "assembly", "body_type"):
            value = label(row.get(field))
            values[field] = (
                MISSING_CATEGORY if value is None else
                value.upper() if value.upper() in {"CNG", "LPG", "PHEV", "CVT", "SUV"} else value.title()
            )
    return {field: values[field] for field in FEATURE_SETS[feature_set]}


def prepare_target(row: Mapping) -> int:
    """Validate the training target separately; prediction inputs need no price."""
    return _integer(row.get("price_pkr"), "price_pkr", 1)


def feature_contract() -> dict:
    """Serializable schema for saving with later fitted model artifacts."""
    return {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "feature_sets": {
            name: {
                "columns": list(fields),
                "numerical": [field for field in fields if field in NUMERICAL_FIELDS],
                "categorical": [field for field in fields if field not in NUMERICAL_FIELDS],
            } for name, fields in FEATURE_SETS.items()
        },
        "missing_category": MISSING_CATEGORY, "missing_numerical": None,
        "target": "price_pkr", "target_unit": "PKR", "model_year_policy": "direct; no derived age",
        "registration_features": "deferred", "fitted_preprocessing": "not fitted; training folds only",
        "prediction_support": "not declared",
    }
