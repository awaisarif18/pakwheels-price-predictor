"""Render coverage and missingness without using targets to fit transformations."""

from collections import Counter, defaultdict
from statistics import median

FIELDS = ["make", "model", "variant", "year", "price_pkr", "mileage_km", "fuel", "transmission", "engine_cc", "listing_city", "assembly", "body_type", "registration_year", "listing_date"]


def coverage(rows: list[dict], dimension: str) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        key = f"{row.get('make') or '<missing>'} {row.get('model') or '<missing>'}" if dimension == "family" else str(row.get(dimension) if row.get(dimension) is not None else "<missing>")
        groups[key].append(row)
    result = []
    for key, members in sorted(groups.items()):
        result.append({
            "category": key, "rows": len(members),
            "modeling_candidates": sum(row["modeling_candidate"] for row in members),
            "source_checked_candidates": sum(row["source_checked_candidate"] for row in members),
            **{f"missing_{field}": sum(row.get(field) is None for row in members) for field in FIELDS},
        })
    return result


def render_quality_report(rows: list[dict], reviews: dict, fingerprints: dict) -> str:
    candidates = [row for row in rows if row["modeling_candidate"]]
    checked = [row for row in rows if row["source_checked_candidate"]]
    checks = Counter(item["status"] for review in reviews.values() for item in review["checks"].values())
    reasons = Counter(reason for row in rows for reason in row["exclusion_reasons"].split(";") if reason)
    lines = [
        "# Pilot batch quality and preparation", "",
        f"Raw observations: {len(rows)}. Candidate rows: {len(candidates)}. Source-checked candidates: {len(checked)}.",
        "", "## Integrity and evidence", "",
        "The original raw/clean exports passed local integrity checks. This report preserves raw files and applies only evidenced corrections to derived copies.",
        f"Cached evidence: {len(reviews)}/{len(rows)} rows, with every referenced HTML checksum checked. Structured field comparisons: {dict(checks)}.",
        "Price verification requires the current listing's visible price box to agree with its URL-matched structured offer. It establishes snapshot agreement, not a verified sale price or seller truth.",
        "", "## Evidenced extraction corrections", "",
        "| Listing ID | Field | Stored value | Evidenced value |", "|---|---|---|---|",
    ]
    for review in reviews.values():
        for field, value in review["updates"].items():
            lines.append(f"| {review['listing_id']} | {field} | {review['checks'][field]['stored'] or '<missing>'} | {value} |")
    lines.extend(["", "Other records without saved evidence are not guessed or silently repaired. See evidence_review.json for comparisons and source paths.", "", "## Candidate scope", "", "Four families, years 2010-2026, all observed cities. Other valid observations stay in normalized_all.csv with exclusion reasons. This is preparation scope, not released predictor support.", "", "| Family | All observed | Candidates | Source-checked candidates |", "|---|---:|---:|---:|"])
    lines.extend(f"| {item['category']} | {item['rows']} | {item['modeling_candidates']} | {item['source_checked_candidates']} |" for item in coverage(rows, "family"))
    lines.extend(["", f"Exclusion reasons, with overlaps allowed: {dict(reasons)}.", "", "## Missingness", "", "Counts below use normalized copies, including evidenced corrections. Source placeholders such as N/A become empty optional values. Zero mileage stays zero. Unspecified variant does not become base trim.", "", "| Field | Normalized observations missing | Candidates missing | Source-checked candidates missing |", "|---|---:|---:|---:|"])
    for field in FIELDS:
        lines.append(f"| {field} | {sum(row.get(field) is None for row in rows)}/{len(rows)} | {sum(row.get(field) is None for row in candidates)}/{len(candidates)} | {sum(row.get(field) is None for row in checked)}/{len(checked)} |")
    lines.extend(["", "Registration meaning remains unknown where stated. Registration gap/usage is not derived. All observed dates are updates, not original publication dates.", "", "## Coverage and small-sample limits", ""])
    for field in ["year", "price_pkr", "mileage_km"]:
        values = [row[field] for row in candidates if row.get(field) is not None]
        if values:
            lines.append(f"- Candidate {field}: min {min(values)}, median {median(values)}, max {max(values)}.")
    variants = Counter((row["make"], row["model"], row.get("variant")) for row in candidates)
    sparse = sum(count <= 3 for count in variants.values())
    cities = Counter(row["listing_city"] for row in candidates)
    lines.extend([
        f"- Candidate family/variant combinations: {len(variants)}; {sparse} have three or fewer observations.",
        f"- Candidate cities: {len(cities)}; {sum(count <= 3 for count in cities.values())} have three or fewer observations.",
        f"- Source-checked split groups: {len({row['group_id'] for row in checked})}. Exact-specification clusters are conservative possible-repost groups, not proof of duplicate vehicles.",
        "", "Family/year/city coverage CSVs report missingness with denominators. Marketplace ordering and the evidence-retention policy make this a convenience sample; no national representativeness claim is made.",
        "", "## Feature and training decisions", "",
        "- F0 retains make/model/year/mileage/city. F1 adds preserved variant. F2 adds fuel/transmission/engine/assembly/body type.",
        "- F3 registration timing is deferred because semantics are unknown and missingness is high.",
        "- Missing optional values remain empty. Training-only encoders, imputers, scalers, and rare-category handling have not been fitted.",
        "- source_checked_candidates.csv is the conservative initial exploratory population. modeling_candidates.csv additionally includes rows whose asking price still lacks cached verification.",
        "- No benchmark, final test, prediction support, or model score exists yet. Obtain deeper corrected collection within this scope before claiming a useful four-family demo.",
        "", "## Input fingerprints", "",
    ])
    lines.extend(f"- {name}: `{value}`" for name, value in fingerprints.items())
    return "\n".join(lines) + "\n"
