"""Compare stored attributes with local source snapshots without network access."""

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from bs4 import BeautifulSoup

NUMERIC_FIELDS = {"price_pkr", "year", "mileage_km", "engine_cc"}


def whole_number(value) -> int | None:
    if value is None or not str(value).strip():
        return None
    try:
        number = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return int(number) if number.is_finite() and number == number.to_integral_value() else None


def _source_number(value) -> int | None:
    match = re.search(r"\d[\d,]*(?:\.\d+)?", str(value)) if value is not None else None
    return whole_number(match.group()) if match else None


def _objects(value):
    if isinstance(value, list):
        for child in value:
            yield from _objects(child)
    elif isinstance(value, dict):
        yield value
        yield from _objects(value.get("@graph", []))


def review_evidence(batch: Path, rows: tuple[dict, ...]) -> dict[str, dict]:
    """Return field comparisons and evidenced corrections keyed by listing ID.

    Corrections are limited to an unambiguous main price agreeing with the
    current product, or explicit structured fuel. All other disagreements
    remain flags. This verifies snapshot agreement, not the seller's facts.
    """
    batch = batch.resolve()
    events = {}
    for path in sorted((batch / "runs").glob("*.json")):
        log = json.loads(path.read_text(encoding="utf-8"))
        for event in log.get("selections", []):
            if event.get("html_evidence"):
                events[event["url"]] = event
    reviews = {}
    for row in rows:
        event = events.get(row["source_url"])
        if not event:
            continue
        review = {"listing_id": row["listing_id"], "checks": {}, "updates": {}, "flags": []}
        reviews[row["listing_id"]] = review
        path = (batch / event["html_evidence"]).resolve()
        if not path.is_relative_to(batch):
            raise ValueError("Evidence path escapes the batch directory")
        content = path.read_bytes()
        fingerprint = hashlib.sha256(content).hexdigest()
        if fingerprint != event["html_sha256"]:
            raise ValueError(f"Evidence checksum mismatch: {row['listing_id']}")
        review.update(html_path=event["html_evidence"], html_sha256=fingerprint)
        soup = BeautifulSoup(content.decode("utf-8"), "lxml")
        heading = soup.find("h1")
        review["source_title"] = " ".join(heading.get_text(" ", strip=True).split()) if heading else None
        products = []
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                decoded = json.loads(script.get_text())
            except ValueError:
                continue
            for product in _objects(decoded):
                offer = product.get("offers")
                if isinstance(offer, dict) and isinstance(offer.get("url"), str) and offer["url"].rstrip("/") == row["source_url"].rstrip("/"):
                    products.append(product)
        review["matched_product_count"] = len(products)
        if len(products) != 1:
            review["flags"].append("no_unique_current_product")
            continue
        product = products[0]
        engine = product.get("vehicleEngine")
        source = {
            "price_pkr": _source_number(product["offers"].get("price")),
            "year": _source_number(product.get("modelDate")),
            "mileage_km": _source_number(product.get("mileageFromOdometer")),
            "engine_cc": _source_number(engine.get("engineDisplacement")) if isinstance(engine, dict) else None,
            "fuel": product.get("fuelType"), "transmission": product.get("vehicleTransmission"),
        }
        price_node = soup.select_one(".price-well .price-box > strong") or soup.select_one(".price-box > strong")
        displayed = price_node.get_text(" ", strip=True) if price_node else ""
        price_match = re.search(r"PKR\s*([\d,]+(?:\.\d+)?)\s*(lacs?|lakhs?|crores?|cr|millions?|mn)?", displayed, re.I)
        dom_price = None
        if price_match:
            amount = Decimal(price_match.group(1).replace(",", ""))
            unit = (price_match.group(2) or "").casefold()
            multiplier = 100_000 if unit.startswith(("lac", "lakh")) else 10_000_000 if unit.startswith("cr") else 1_000_000 if unit.startswith(("million", "mn")) else 1
            dom_price = whole_number(amount * multiplier)
        review["price_box_displayed"] = displayed or None
        review["price_box_value"] = dom_price
        review["price_verified"] = dom_price is not None and dom_price == source["price_pkr"]
        if not review["price_verified"]:
            review["flags"].append("price_box_product_disagreement_or_unavailable")
        for field, actual in source.items():
            if actual is None or actual == "":
                continue
            stored = whole_number(row[field]) if field in NUMERIC_FIELDS else row[field].casefold()
            expected = actual if field in NUMERIC_FIELDS else str(actual).casefold()
            mismatch = stored != expected
            review["checks"][field] = {"stored": row[field], "source": actual, "status": "mismatch" if mismatch else "match"}
            if mismatch:
                if field == "price_pkr" and review["price_verified"]:
                    review["updates"][field] = actual
                elif field == "fuel" and actual in {"Petrol", "Diesel", "Hybrid", "CNG", "Electric", "LPG", "PHEV"}:
                    review["updates"][field] = actual
                else:
                    review["flags"].append(f"unresolved_source_disagreement:{field}")
    return reviews
