"""Extract optional fields from the current listing, preserving their meaning.

Identity names retain the source spelling with normalized whitespace. Variant
extraction is provisional until a reviewed catalogue establishes canonical names.
Missing optional evidence never makes an otherwise complete listing incomplete.
"""

import json
import re
from datetime import datetime
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

SCHEMA_VERSION = 2
OPTIONAL_COLUMNS = [
    "make", "model", "variant", "identity_status", "assembly", "body_type",
    "registration_year", "registration_year_meaning", "registration_year_source",
    "registration_year_status", "listing_date", "listing_date_type",
    "field_provenance", "collection_schema_version",
]


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _url_key(value: str) -> tuple[str, str]:
    parsed = urlsplit(value)
    return parsed.hostname or "", parsed.path.rstrip("/")


def _objects(value):
    if isinstance(value, list):
        for child in value:
            yield from _objects(child)
    elif isinstance(value, dict):
        yield value
        yield from _objects(value.get("@graph", []))


def _listing_product(soup: BeautifulSoup, url: str) -> dict:
    matches = {}
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            decoded = json.loads(script.get_text())
        except (ValueError, TypeError):
            continue
        for item in _objects(decoded):
            kinds = item.get("@type", [])
            if isinstance(kinds, str):
                kinds = [kinds]
            if not isinstance(kinds, list) or not any(kind in ("Product", "Car", "Vehicle") for kind in kinds if isinstance(kind, str)):
                continue
            offers = item.get("offers", [])
            if isinstance(offers, dict):
                offers = [offers]
            if not isinstance(offers, list):
                continue
            if any(
                isinstance(offer, dict) and isinstance(offer.get("url"), str)
                and _url_key(offer["url"]) == _url_key(url)
                for offer in offers
            ):
                matches[json.dumps(item, sort_keys=True)] = item
    # Conflicting descriptions of the same listing require investigation.
    return next(iter(matches.values())) if len(matches) == 1 else {}


def extract_fields(soup: BeautifulSoup, url: str, title: str, year: int | None) -> dict:
    """Return optional fields and compact provenance, without network or writes.

    Call before deleting script tags. Only URL-matched structured data, labeled
    main-listing details, and explicit registration statements are accepted.
    """
    result = dict.fromkeys(OPTIONAL_COLUMNS)
    result.update(
        identity_status="unmatched", registration_year_status="not_stated",
        collection_schema_version=SCHEMA_VERSION,
    )
    provenance = {}
    product = _listing_product(soup, url)
    brand = product.get("brand")
    make = brand.get("name") if isinstance(brand, dict) else brand
    model = product.get("model")
    if isinstance(make, str) and make.strip() and isinstance(model, str) and model.strip():
        result["make"], result["model"] = _text(make), _text(model)
        provenance["make"] = {"source": "url_matched_json_ld.brand.name"}
        provenance["model"] = {"source": "url_matched_json_ld.model"}
        result["identity_status"] = "family_extracted_variant_unmatched"
        if year is not None:
            prefix = re.escape(f"{result['make']} {result['model']}")
            match = re.fullmatch(prefix + r"(?:\s+(.*?))?\s+" + str(year), _text(title), re.I)
            if match:
                result["variant"] = _text(match.group(1) or "") or None
                result["identity_status"] = "extracted_pending_review"
                if result["variant"]:
                    provenance["variant"] = {"source": "h1_minus_verified_make_model_and_year"}

    details = soup.select_one("#scroll_car_detail")
    if details:
        labels = {}
        for label in details.select("li.ad-data"):
            sibling = label.find_next_sibling("li")
            if sibling and "ad-data" not in sibling.get("class", []):
                key = _text(label.get_text(" ", strip=True)).rstrip(":").casefold()
                labels[key] = _text(sibling.get_text(" ", strip=True))
        for field, label in [("assembly", "assembly"), ("body_type", "body type")]:
            if labels.get(label):
                result[field] = labels[label]
                provenance[field] = {"source": f"scroll_car_detail.{label}"}
        for label, date_type in [("last updated", "updated"), ("posted on", "posted"), ("date added", "posted")]:
            if not labels.get(label):
                continue
            displayed = labels[label]
            provenance["listing_date"] = {"source": f"scroll_car_detail.{label}", "displayed": displayed}
            result["listing_date_type"] = date_type
            for date_format in ["%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"]:
                try:
                    result["listing_date"] = datetime.strptime(displayed, date_format).date().isoformat()
                    break
                except ValueError:
                    continue
            break

    if result["body_type"] is None and isinstance(product.get("bodyType"), str):
        result["body_type"] = _text(product["bodyType"]) or None
        if result["body_type"]:
            provenance["body_type"] = {"source": "url_matched_json_ld.bodyType"}

    heading = soup.select_one("#scroll_seller_comments")
    comments = heading.find_next_sibling() if heading else None
    candidates = []
    if comments and comments.name == "div":
        for line in comments.get_text("\n", strip=True).splitlines():
            line = _text(line)
            match = re.fullmatch(
                r"(?:Registered(?:\s+(?:in|year))?|Registration(?:\s+year)?)"
                r"\s*[:\-]?\s*((?:19|20)\d{2})[.!]?", line, re.I,
            )
            if match:
                candidates.append((int(match.group(1)), "unknown", line))
                continue
            match = re.fullmatch(
                r"First\s+(?:registration\s+in\s+([A-Za-z ]+)|"
                r"(Pakistan)\s+registration)(?:\s+year)?\s*:\s*((?:19|20)\d{2})[.!]?",
                line, re.I,
            )
            if match:
                jurisdiction = _text(match.group(1) or match.group(2))
                meaning = "first_pakistan_registration" if jurisdiction.casefold() == "pakistan" else "first_registration_other_jurisdiction"
                candidates.append((int(match.group(3)), meaning, line))
    if candidates:
        values = {(value, meaning) for value, meaning, _ in candidates}
        provenance["registration_year"] = {
            "source": "explicit_seller_registration_statement",
            "statements": [line for _, _, line in candidates],
        }
        result["registration_year_source"] = "explicit_seller_registration_statement"
        if len(values) == 1:
            result["registration_year"], result["registration_year_meaning"] = next(iter(values))
            result["registration_year_status"] = "extracted"
        else:
            result["registration_year_status"] = "conflicting"

    result["field_provenance"] = json.dumps(provenance, sort_keys=True, ensure_ascii=False)
    return result
