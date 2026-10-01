"""Inspect stored CSV evidence without changing it or fetching source pages."""

import csv
import hashlib
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED_COLUMNS = {
    "listing_id", "car_title", "year", "price_pkr", "mileage_km",
    "fuel", "transmission", "engine_cc", "listing_city", "source_url",
    "collected_at", "parse_status", "missing_fields",
}
CORE_FIELDS = ("car_title", "year", "price_pkr", "mileage_km")


@dataclass(frozen=True)
class AuditIssue:
    row_number: int
    listing_id: str
    field: str
    reason: str


@dataclass(frozen=True)
class DatasetAudit:
    path: Path
    sha256: str
    rows: tuple[dict[str, str], ...]
    unique_ids: int
    unique_urls: int
    duplicate_ids: dict[str, int]
    duplicate_urls: dict[str, int]
    parse_statuses: dict[str, int]
    missing_fields: dict[str, int]
    fuel_counts: dict[str, int]
    transmission_counts: dict[str, int]
    city_counts: dict[str, int]
    issues: tuple[AuditIssue, ...]

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def complete_count(self) -> int:
        return self.parse_statuses.get("complete", 0)


def _counts(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(value or "<missing>" for value in values).items()))


def _duplicates(values: list[str]) -> dict[str, int]:
    return dict(sorted(
        (value, count) for value, count in Counter(values).items()
        if value and count > 1
    ))


def _numeric_issue(value: str, field: str) -> str | None:
    try:
        number = Decimal(value)
    except InvalidOperation:
        return "Not a valid number"
    if not number.is_finite():
        return "Non-finite number"
    if number != number.to_integral_value():
        return "Expected a whole-number value"
    if field == "mileage_km" and number < 0:
        return "Mileage cannot be negative"
    if field != "mileage_km" and number <= 0:
        return "Value must be positive"
    if field == "year" and not 1900 <= number <= 2100:
        return "Year is outside the audit sanity range; review source"
    return None


def audit_csv(path: Path) -> DatasetAudit:
    """Return stored-file statistics and flags without certifying source values.

    Raises ValueError for missing columns or malformed row shapes. A valid
    header with no data rows is supported. Optional missing attributes are
    counted without assigning defaults or assuming extraction failures.
    """
    path = path.resolve()
    content = path.read_bytes()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing_columns = REQUIRED_COLUMNS.difference(reader.fieldnames or ())
        if missing_columns:
            fields = ", ".join(sorted(missing_columns))
            raise ValueError(f"{path.name}: missing columns: {fields}")
        if len(reader.fieldnames or ()) != len(set(reader.fieldnames or ())):
            raise ValueError(f"{path.name}: duplicate column names")
        rows = []
        for row_number, source_row in enumerate(reader, start=2):
            if None in source_row or any(value is None for value in source_row.values()):
                raise ValueError(f"{path.name}: malformed CSV at row {row_number}")
            rows.append({field: value.strip() for field, value in source_row.items()})

    issues = []
    for row_number, row in enumerate(rows, start=2):
        def flag(field: str, reason: str) -> None:
            issues.append(AuditIssue(row_number, row["listing_id"], field, reason))

        for field in ("listing_id", "source_url", "collected_at"):
            if not row[field]:
                flag(field, "Missing provenance value")
        if row["parse_status"] not in {"complete", "incomplete"}:
            flag("parse_status", "Unknown parse status")
        for field in CORE_FIELDS:
            if not row[field] and row["parse_status"] == "complete":
                flag(field, "Complete row has a missing core field")
        if row["parse_status"] == "complete" and row["missing_fields"]:
            flag("missing_fields", "Complete row declares missing core fields")
        for field in ("year", "price_pkr", "mileage_km", "engine_cc"):
            if row[field]:
                reason = _numeric_issue(row[field], field)
                if reason:
                    flag(field, reason)

    ids = [row["listing_id"] for row in rows]
    urls = [row["source_url"] for row in rows]
    return DatasetAudit(
        path=path,
        sha256=hashlib.sha256(content).hexdigest(),
        rows=tuple(rows),
        unique_ids=len({value for value in ids if value}),
        unique_urls=len({value for value in urls if value}),
        duplicate_ids=_duplicates(ids),
        duplicate_urls=_duplicates(urls),
        parse_statuses=_counts([row["parse_status"] for row in rows]),
        missing_fields={field: sum(not row[field] for row in rows) for field in sorted(REQUIRED_COLUMNS)},
        fuel_counts=_counts([row["fuel"] for row in rows]),
        transmission_counts=_counts([row["transmission"] for row in rows]),
        city_counts=_counts([row["listing_city"] for row in rows]),
        issues=tuple(issues),
    )


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def render_report(raw: DatasetAudit, clean: DatasetAudit, generated_at: str) -> str:
    """Describe local checks and the source review that remains necessary."""
    lines = [
        "# Initial stored-data audit", "", f"Generated at: {generated_at}", "",
        "This report checks local CSV structure and values. Manual source verification, "
        "identity normalization, repost grouping, and training eligibility remain pending.", "",
        "## File summary", "",
        "| Measure | Raw export | Parser-complete export |", "|---|---:|---:|",
    ]
    measures = [
        ("Stored rows", raw.row_count, clean.row_count),
        ("Unique nonempty listing IDs", raw.unique_ids, clean.unique_ids),
        ("Unique nonempty URLs", raw.unique_urls, clean.unique_urls),
        ("Rows marked complete", raw.complete_count, clean.complete_count),
        ("Repeated listing IDs", len(raw.duplicate_ids), len(clean.duplicate_ids)),
        ("Repeated URLs", len(raw.duplicate_urls), len(clean.duplicate_urls)),
        ("Missing engine displacement", raw.missing_fields["engine_cc"], clean.missing_fields["engine_cc"]),
        ("Integrity flags", len(raw.issues), len(clean.issues)),
    ]
    lines.extend(f"| {label} | {left} | {right} |" for label, left, right in measures)
    raw_complete = Counter(tuple(sorted(row.items())) for row in raw.rows if row["parse_status"] == "complete")
    clean_records = Counter(tuple(sorted(row.items())) for row in clean.rows)
    match = "Yes" if raw_complete == clean_records else "No; investigate"
    lines.extend([
        "", f"Clean export matches all complete raw rows: {match}.", "",
        "Parser completeness uses stored rows as its denominator. Request success and "
        "manual extraction correctness cannot be inferred from these files.", "",
        "## Raw field coverage", "",
        "An empty `missing_fields` value means no core fields were reported missing; "
        "it is expected for parser-complete rows.", "",
        "| Field | Missing rows | Total rows |", "|---|---:|---:|",
    ])
    lines.extend(f"| {field} | {count} | {raw.row_count} |" for field, count in raw.missing_fields.items())
    for heading, counts in (
        ("Fuel", raw.fuel_counts), ("Transmission", raw.transmission_counts), ("Listing city", raw.city_counts),
    ):
        lines.extend(["", f"## {heading}", "", "| Stored label | Count |", "|---|---:|"])
        lines.extend(f"| {_cell(label)} | {count} |" for label, count in counts.items())
    lines.extend(["", "## Integrity flags", ""])
    has_flags = raw_complete != clean_records or any(
        audit.issues or audit.duplicate_ids or audit.duplicate_urls for audit in (raw, clean)
    )
    if not has_flags:
        lines.append("No flags from the implemented local checks. This is not a source-correctness certification.")
    else:
        lines.extend(["| File | CSV row | Listing ID or value | Field | Reason |", "|---|---:|---|---|---|"])
        if raw_complete != clean_records:
            lines.append("| Cross-export | All | All | rows | Clean export differs from complete raw rows |")
        for audit in (raw, clean):
            for issue in audit.issues:
                cells = (audit.path.name, issue.row_number, issue.listing_id, issue.field, issue.reason)
                lines.append("| " + " | ".join(_cell(value) for value in cells) + " |")
            for field, duplicates in (("listing_id", audit.duplicate_ids), ("source_url", audit.duplicate_urls)):
                for value, count in duplicates.items():
                    cells = (audit.path.name, "Multiple", value, field, f"Appears {count} times")
                    lines.append("| " + " | ".join(_cell(value) for value in cells) + " |")
    lines.extend([
        "", "## Next manual checks", "",
        "1. Verify the main asking price, year, and mileage against available source evidence.",
        "2. Record how fuel, transmission, city, and engine displacement were extracted.",
        "3. Confirm EV displacement non-applicability rather than inventing a value.",
        "4. Review make/model/variant in `identity_review.csv`; retain meaningful trim wording.",
        "5. Record unavailable evidence and suspected reposts before deciding training eligibility.",
        "", "## Input fingerprints", "",
    ])
    for audit in (raw, clean):
        lines.extend([f"- File: `{audit.path.as_posix()}`", f"  SHA-256: `{audit.sha256}`"])
    return "\n".join(lines) + "\n"


def seed_identity_review(audit: DatasetAudit, path: Path) -> bool:
    """Create a pending worksheet once; return False if it already exists."""
    fields = (
        "listing_id", "original_title", "source_url", "proposed_make", "proposed_model",
        "proposed_variant", "identity_status", "source_verification", "notes",
    )
    try:
        stream = path.open("x", encoding="utf-8", newline="")
    except FileExistsError:
        return False
    with stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in audit.rows:
            writer.writerow({
                "listing_id": row["listing_id"], "original_title": row["car_title"],
                "source_url": row["source_url"], "identity_status": "pending",
                "source_verification": "not_reviewed",
            })
    return True
