"""PKR errors and descriptive subgroup reporting for held-out predictions."""

from collections import defaultdict

import numpy as np


def regression_metrics(actual, predicted) -> dict:
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if actual.ndim != 1 or actual.shape != predicted.shape or not len(actual):
        raise ValueError("Metrics need aligned, nonempty one-dimensional predictions")
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all() or (actual <= 0).any():
        raise ValueError("Metrics require positive finite targets and finite predictions")
    errors = np.abs(predicted - actual)
    return {
        "count": len(actual), "mae_pkr": float(errors.mean()),
        "median_ae_pkr": float(np.median(errors)),
        "median_ape_pct": float(np.median(100 * errors / actual)),
        "rmse_pkr": float(np.sqrt(np.mean(errors ** 2))),
        "nonpositive_predictions": int((predicted <= 0).sum()),
    }


def price_band(price: float) -> str:
    if price < 2_000_000:
        return "under_2m"
    if price < 4_000_000:
        return "2m_to_under_4m"
    if price < 6_000_000:
        return "4m_to_under_6m"
    return "6m_and_above"


def summarize_predictions(predictions: list[dict]) -> list[dict]:
    """Pool each row's one held-out prediction; never mix different experiments."""
    groups = defaultdict(list)
    for row in predictions:
        dimensions = {
            "overall": "all", "family": row["family"],
            "variant": row["family"] + " / " + row["variant"],
            "year": str(row["year"]), "city": row["listing_city"],
            "price_band": price_band(row["actual_pkr"]),
            "variant_seen": "unseen" if row["unseen_variant"] else "seen",
            "city_seen": "unseen" if row["unseen_city"] else "seen",
        }
        for dimension, value in dimensions.items():
            groups[(row["experiment"], dimension, value)].append(row)
    return [
        {"experiment": experiment, "dimension": dimension, "value": value,
         **regression_metrics([row["actual_pkr"] for row in rows], [row["predicted_pkr"] for row in rows])}
        for (experiment, dimension, value), rows in sorted(groups.items())
    ]
