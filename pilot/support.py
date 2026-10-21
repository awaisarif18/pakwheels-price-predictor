"""Development-only coverage bounds and deterministic inference refusals."""

from collections import defaultdict

from pilot.features import MISSING_CATEGORY


def family_name(row):
    return row["make"] + " " + row["model"]


def _groups_by(data, indices, field):
    counts = defaultdict(set)
    for index in indices:
        counts[data.inputs[index][field]].add(data.group_ids[index])
    return counts


def build_support(data, policy):
    families, variants = defaultdict(list), defaultdict(list)
    for index, row in enumerate(data.inputs):
        families[family_name(row)].append(index)
        variants[row["make"], row["model"], row["variant"]].append(index)
    coverage = policy["coverage"]
    entries = []
    for key, indices in sorted(variants.items()):
        family_indices = families[key[0] + " " + key[1]]
        if key[2] == MISSING_CATEGORY or len({data.group_ids[i] for i in family_indices}) < coverage["min_family_groups"]:
            continue
        years = {value for value, groups in _groups_by(data, family_indices, "year").items()
                 if len(groups) >= coverage["min_family_year_groups"]}
        cities = {value for value, groups in _groups_by(data, family_indices, "listing_city").items()
                  if len(groups) >= coverage["min_family_city_groups"]}
        eligible = [i for i in indices if data.inputs[i]["year"] in years and data.inputs[i]["listing_city"] in cities]
        if len({data.group_ids[i] for i in eligible}) < coverage["min_variant_groups"] or len(
            {data.validation_folds[i] for i in eligible}
        ) != coverage["required_folds"]:
            continue
        rows = [data.inputs[i] for i in eligible]
        configurations = {tuple(row[field] for field in ("transmission", "engine_cc", "assembly")) for row in rows}
        entries.append({"make": key[0], "model": key[1], "variant": key[2], "development_rows": len(rows),
                        "development_groups": len({data.group_ids[i] for i in eligible}),
                        "years": sorted({row["year"] for row in rows}), "cities": sorted({row["listing_city"] for row in rows}),
                        "mileage_km": [min(row["mileage_km"] for row in rows), max(row["mileage_km"] for row in rows)],
                        "configurations": [dict(zip(("transmission", "engine_cc", "assembly"), values))
                                           for values in sorted(configurations, key=str)]})
    if not entries:
        raise ValueError("No variants have enough development coverage for the demo")
    return {"support_schema_version": 1, "basis": "development_only", "entries": entries}


def support_reason(row, support):
    entry = next((item for item in support["entries"] if all(row[field] == item[field] for field in ("make", "model", "variant"))), None)
    if entry is None:
        return "This variant does not have enough coverage for the pilot demo"
    if row["year"] not in entry["years"]:
        return "This model year is outside the observed supported years for this variant"
    if row["listing_city"] not in entry["cities"]:
        return "This listing city is outside the supported cities for this variant"
    if not entry["mileage_km"][0] <= row["mileage_km"] <= entry["mileage_km"][1]:
        return "Mileage is outside the observed supported range for this variant"
    if not any(all(row[field] == values[field] for field in ("transmission", "engine_cc", "assembly")) for values in entry["configurations"]):
        return "Transmission, engine capacity, and assembly do not match an observed supported configuration"
    return None
