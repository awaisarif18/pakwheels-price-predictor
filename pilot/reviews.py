"""Apply explicit human quality decisions while preserving source observations."""

import json

from pilot.paths import PROJECT_ROOT

REVIEW_PATH = PROJECT_ROOT / "configs/manual_reviews.json"


def load_reviews(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("version") != 1:
        raise ValueError("Unsupported manual-review version")
    decisions = {}
    for item in value.get("decisions", []):
        number = item.get("listing_id")
        if not isinstance(number, str) or not number.isdigit() or number in decisions:
            raise ValueError("Manual reviews require unique numeric listing IDs")
        if item.get("decision") not in {"exclude", "keep"} or not item.get("reason"):
            raise ValueError("Manual reviews require an explicit decision and reason")
        for field, correction in item.get("corrections", {}).items():
            if (field != "mileage_km" or item["decision"] != "keep" or
                    any(type(correction.get(key)) is not int or correction[key] < 0 for key in ("from", "to"))):
                raise ValueError("Mileage corrections require explicit nonnegative integer from/to values")
        if "accept_price_precision" in item:
            accepted = item["accept_price_precision"]
            if item["decision"] != "keep" or any(type(accepted.get(key)) is not int or accepted[key] <= 0 for key in ("displayed_pkr", "structured_pkr")):
                raise ValueError("Accepted price precision requires explicit positive displayed/structured prices")
        decisions[number] = item
    return decisions


def _apply_kept_values(row, decision, evidence):
    updates = json.loads(row.get("manual_updates") or "{}")
    for field, correction in decision.get("corrections", {}).items():
        if row[field] not in (correction["from"], correction["to"]):
            raise ValueError(f"Manual {field} correction no longer matches listing {row['listing_id']}")
        row[field] = correction["to"]
        updates[field] = correction
    row["manual_updates"] = json.dumps(updates, sort_keys=True)
    accepted = decision.get("accept_price_precision")
    if accepted:
        review = evidence.get(row.get("source_batch"), {}).get(row["listing_id"], {})
        others = [flag for flag in review.get("flags", []) if flag.startswith("unresolved_source_disagreement:") and not flag.endswith(":price_pkr")]
        if (review.get("price_box_value") != accepted["displayed_pkr"] or
                review.get("checks", {}).get("price_pkr", {}).get("source") != accepted["structured_pkr"] or
                row["price_pkr"] != accepted["displayed_pkr"] or others):
            raise ValueError("Accepted price precision no longer matches the saved source evidence")
        reasons = set(filter(None, row["exclusion_reasons"].split(";"))) - {"unresolved_source_disagreement"}
        row.update(manual_price_accepted=True, exclusion_reasons=";".join(sorted(reasons)),
                   modeling_candidate=not reasons, source_checked_candidate=not reasons)
    return row


def apply_reviews(rows, decisions, evidence_by_batch=None):
    """Return copies; retain every row and add explicit exclusion reasons.

    Explicit accepted price pairs can resolve their exact price disagreement;
    other eligibility failures remain. Raw source-agreement flags stay intact.
    """
    excluded = {number for number, item in decisions.items() if item["decision"] == "exclude"}
    groups = {row["group_id"] for row in rows if row["listing_id"] in excluded}
    result = []
    for original in rows:
        row = dict(original)
        decision = decisions.get(row["listing_id"], {})
        row.setdefault("manual_updates", "{}")
        row.setdefault("manual_price_accepted", False)
        row["manual_review_decision"] = decision.get("decision", "")
        if decision.get("decision") == "keep":
            row = _apply_kept_values(row, decision, evidence_by_batch or {})
        if row["group_id"] in groups:
            reason = "manual_review_excluded" if row["listing_id"] in excluded else "group_linked_to_manual_review_exclusion"
            reasons = set(filter(None, row["exclusion_reasons"].split(";"))) | {reason}
            row.update(exclusion_reasons=";".join(sorted(reasons)), modeling_candidate=False, source_checked_candidate=False)
        result.append(row)
    return result


def reject_excluded_population(rows):
    """Refuse stale populations instead of silently changing frozen membership."""
    decisions = load_reviews(REVIEW_PATH)
    excluded = {number for number, item in decisions.items() if item["decision"] == "exclude"}
    found = sorted({row["listing_id"] for row in rows} & excluded)
    if found:
        raise ValueError("Dataset includes manually excluded listing IDs: " + ", ".join(found) +
                         ". Prepare a new reviewed dataset and evaluation version before modeling.")
    for row in rows:
        decision = decisions.get(row["listing_id"], {})
        if str(row.get("manual_price_accepted")) == "True":
            accepted = decision.get("accept_price_precision", {})
            if int(row["price_pkr"]) != accepted.get("displayed_pkr"):
                raise ValueError("Dataset has an unapproved manual price acceptance; prepare a new reviewed version")
        for field, correction in decision.get("corrections", {}).items():
            if int(row[field]) != correction["to"]:
                raise ValueError("Dataset predates a manual correction; prepare a new reviewed dataset and evaluation version")
