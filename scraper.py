"""Small, sequential PakWheels research collector (use only with authorized access).

Install: pip install requests beautifulsoup4 pandas lxml
Try parser offline: python scraper.py --self-test
Try one permitted ad: python scraper.py --url 'https://www.pakwheels.com/used-cars/...'
Try limited search: python scraper.py --pages 1 --ads 10 --delay 5

The script never solves CAPTCHAs or circumvents access restrictions. It records
incomplete rows in pakwheels_raw.csv and complete rows in pakwheels_clean.csv.
"""

import argparse
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pandas as pd
import requests
from bs4 import BeautifulSoup

from collector.fields import OPTIONAL_COLUMNS, extract_fields
from collector.runner import CollectionSettings, run_collection
from collector.sampling import SearchSpec, load_plan

BASE_URL = "https://www.pakwheels.com"
SEARCH_URL = BASE_URL + "/used-cars/search/-/?page={page}"
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data" / "raw" / "current"
RAW_FILE = DATA_DIR / "pakwheels_raw.csv"
CLEAN_FILE = DATA_DIR / "pakwheels_clean.csv"
DEBUG_DIR = PROJECT_DIR / "data" / "debug_pages"

COLUMNS = [
    "listing_id", "car_title", "year", "price_pkr", "mileage_km",
    "fuel", "transmission", "engine_cc", "listing_city", "source_url",
    "collected_at", "parse_status", "missing_fields",
] + OPTIONAL_COLUMNS

AD_PATH = re.compile(r"/used-cars/.+-for-sale-in-.+-\d+/?$", re.I)
YEAR_PATTERN = re.compile(r"\b(?:19|20)\d{2}\b")
PRICE_PATTERN = re.compile(
    r"\bPKR\s*([\d,]+(?:\.\d+)?)\s*"
    r"(crores?|cr|lakhs?|lacs?|millions?|mn)?\b", re.I
)
MILEAGE_PATTERN = re.compile(r"\b([\d,]+)\s*(?:kilometres|kilometers|kms?|KM)\b", re.I)
FUEL_PATTERN = re.compile(r"\b(Petrol|Diesel|Hybrid|CNG|Electric|LPG)\b", re.I)
TRANSMISSION_PATTERN = re.compile(r"\b(Automatic|Manual|CVT)\b", re.I)
ENGINE_PATTERN = re.compile(r"\b(\d{2,5})\s*cc\b", re.I)


class AccessRestricted(RuntimeError):
    """Access needs clarification/approval; do not retry around restrictions."""


def normalize_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def fetch_page(session, url, delay):
    time.sleep(delay)
    response = session.get(url, timeout=30)
    if response.status_code in (401, 403, 429):
        raise AccessRestricted(
            f"HTTP {response.status_code} at {url}. Stop here and request "
            "an approved access method from your PakWheels contact."
        )
    response.raise_for_status()
    return response.text


def listing_links(html):
    """Keep search-card order, unlike sorted(set(...)) which over-samples Audi."""
    soup = BeautifulSoup(html, "lxml")
    ordered = dict()
    for anchor in soup.select("a[href]"):
        url = urljoin(BASE_URL, anchor["href"])
        parsed = urlsplit(url)
        if parsed.hostname not in {"www.pakwheels.com", "pakwheels.com"}:
            continue
        path = parsed.path.rstrip("/")
        if AD_PATH.fullmatch(path):
            canonical_url = BASE_URL + path
            ordered[canonical_url] = None
    return list(ordered)


def numeric_price(amount, unit):
    number = float(amount.replace(",", ""))
    unit = (unit or "").lower()
    if unit.startswith(("lac", "lakh")):
        number *= 100_000
    elif unit.startswith(("cr", "crore")):
        number *= 10_000_000
    elif unit.startswith(("million", "mn")):
        number *= 1_000_000
    return int(round(number))


def parse_car(html, url):
    """Parse the visible main listing. Null fields are preserved for debugging."""
    soup = BeautifulSoup(html, "lxml")
    heading = soup.find("h1")
    title = normalize_text(heading.get_text(" ", strip=True)) if heading else ""
    title_years = YEAR_PATTERN.findall(title)
    optional = extract_fields(soup, url, title, int(title_years[-1]) if title_years else None)

    # Exclude invisible scripts/styles; retain document order of visible text.
    for node in soup.select("script, style, noscript, svg"):
        node.decompose()
    body = soup.body or soup
    page_text = normalize_text(body.get_text(" ", strip=True))
    title = normalize_text(heading.get_text(" ", strip=True)) if heading else ""
    position = page_text.find(title) if title else -1
    following = page_text[position + len(title):] if position >= 0 else page_text
    # Exclude sellers' details and unrelated recommended advertisements.
    primary = re.split(
        r"\b(?:Seller Details|Similar Used Cars|Recommended Cars|You May Also Like)\b",
        following, maxsplit=1, flags=re.I
    )[0]

    # The prominent price normally occurs shortly after the h1, e.g. PKR 4,300,000.
    # Some pages instead show "Current Price PKR 43 lacs" lower down.
    price_match = PRICE_PATTERN.search(primary[:3500])
    if not price_match:
        price_match = re.search(
            r"Current\s+Price\s*:?[\s\S]{0,100}?" + PRICE_PATTERN.pattern,
            primary, re.I
        )
    price = numeric_price(price_match.group(1), price_match.group(2)) if price_match else None
    # An unconverted decimal without a unit is not a valid total PKR asking price.
    if price is not None and price < 10_000:
        price = None

    years = YEAR_PATTERN.findall(title)
    if not years:
        years = YEAR_PATTERN.findall(primary[:1000])
    year = int(years[-1]) if years else None

    # Mileage in PakWheels' summary typically looks like "2022 | 66,000 km".
    mileage_match = MILEAGE_PATTERN.search(primary[:3500])
    mileage = int(mileage_match.group(1).replace(",", "")) if mileage_match else None

    # Search around the mileage to avoid unrelated fuel words in ad description.
    near_mileage = (
        primary[mileage_match.end():mileage_match.end() + 180]
        if mileage_match else primary[:700]
    )
    fuel_match = FUEL_PATTERN.search(near_mileage)
    transmission_match = TRANSMISSION_PATTERN.search(near_mileage)
    engine_match = ENGINE_PATTERN.search(primary[:4500])

    path = urlsplit(url).path.rstrip("/")
    id_match = re.search(r"-(\d+)$", path)
    city_match = re.search(r"-for-sale-in-(.+)-\d+$", path, re.I)
    missing = [
        field for field, value in (
            ("title", title or None),
            ("price_pkr", price),
            ("year", year),
            ("mileage_km", mileage),
        ) if value is None
    ]
    row = {
        "listing_id": id_match.group(1) if id_match else None,
        "car_title": title or None,
        "year": year,
        "price_pkr": price,
        "mileage_km": mileage,
        "fuel": fuel_match.group(1).title() if fuel_match else None,
        "transmission": transmission_match.group(1).title() if transmission_match else None,
        "engine_cc": int(engine_match.group(1)) if engine_match else None,
        "listing_city": city_match.group(1).replace("-", " ").title() if city_match else None,
        "source_url": url,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "parse_status": "complete" if not missing else "incomplete",
        "missing_fields": ", ".join(missing),
        **optional,
    }
    return row, primary[:3000]


def save_debug(html, url, row, text_preview):
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    ad_id = row["listing_id"] or "unknown"
    (DEBUG_DIR / f"failed_{ad_id}.html").write_text(html, encoding="utf-8")
    (DEBUG_DIR / f"failed_{ad_id}.txt").write_text(
        f"URL: {url}\nMissing: {row['missing_fields']}\n"
        f"Title: {row['car_title']}\n\nVISIBLE CONTENT:\n{text_preview}\n",
        encoding="utf-8",
    )


def load_existing(output_dir=None):
    raw_file = Path(output_dir) / RAW_FILE.name if output_dir is not None else RAW_FILE
    if not raw_file.exists():
        return {}
    previous = pd.read_csv(raw_file, dtype={"listing_id": "string"})
    if "source_url" not in previous.columns:
        raise ValueError(f"Cannot resume {raw_file}: source_url column is missing")
    if previous["source_url"].isna().any() or previous["source_url"].duplicated().any():
        raise ValueError(f"Cannot resume {raw_file}: source URLs are empty or duplicated")
    previous = previous.where(pd.notna(previous), None)
    return {str(row["source_url"]): row for row in previous.to_dict("records")}


def save_csv(records, output_dir=None):
    directory = Path(output_dir) if output_dir is not None else DATA_DIR
    raw_file = directory / RAW_FILE.name if output_dir is not None else RAW_FILE
    clean_file = directory / CLEAN_FILE.name if output_dir is not None else CLEAN_FILE
    directory.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records.values(), columns=COLUMNS)
    raw_temporary = raw_file.with_suffix(".csv.tmp")
    df.to_csv(raw_temporary, index=False)
    raw_temporary.replace(raw_file)
    clean = df[df["parse_status"] == "complete"].copy()
    clean_temporary = clean_file.with_suffix(".csv.tmp")
    clean.to_csv(clean_temporary, index=False)
    clean_temporary.replace(clean_file)
    return len(df), len(clean)


def run_self_test():
    fixture1 = """<html><body><h1>Honda City 1.2L CVT 2022</h1>
    <div>Islamabad Islamabad PKR 4,300,000</div>
    <div>2022 | 66,000 km | Petrol | Automatic</div><div>1200 cc</div>
    <h3>Current Price PKR 43 lacs</h3></body></html>"""
    first, _ = parse_car(
        fixture1, BASE_URL + "/used-cars/honda-city-2022-for-sale-in-islamabad-12001735"
    )
    assert first["parse_status"] == "complete", first
    assert first["price_pkr"] == 4_300_000 and first["mileage_km"] == 66_000, first
    assert first["transmission"] == "Automatic" and first["engine_cc"] == 1200, first

    fixture2 = """<html><body><h1>Honda Civic Oriel 2021</h1>
    <div>2021 | 35,000 km | Petrol | Automatic</div>
    <h3>Current Price PKR 58.5 lacs</h3></body></html>"""
    second, _ = parse_car(
        fixture2, BASE_URL + "/used-cars/honda-civic-2021-for-sale-in-lahore-12345678"
    )
    assert second["parse_status"] == "complete", second
    assert second["price_pkr"] == 5_850_000 and second["year"] == 2021, second
    print("2 offline parser self-tests passed. (Live access not tested.)")


def main():
    parser = argparse.ArgumentParser(description="Authorized PakWheels price-research collector")
    parser.add_argument("--pages", type=int, help="Search-page limit for general discovery (default: 1)")
    parser.add_argument("--ads", type=int, help="Maximum detail request attempts; saved-row skips do not consume this budget (default: 10, or plan total)")
    parser.add_argument("--delay", type=float, default=5, help="Seconds between HTTP requests (default: 5)")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--url", type=str, help="Test one specific permitted car listing URL")
    selection.add_argument("--sampling-plan", type=Path, help="JSON family searches, quotas, and request/page limits")
    parser.add_argument("--output-dir", type=Path, help="Separate batch directory; default: data/raw/current")
    parser.add_argument("--refresh", action="store_true", help="Re-fetch selected saved complete listings to populate the new schema")
    parser.add_argument("--start-page", type=int, default=1, help="First search page (default: 1)")
    parser.add_argument("--contact", default="your-email@example.com", help="Research collector contact address")
    parser.add_argument("--self-test", action="store_true", help="Run parser tests without network")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return
    if (args.pages is not None and args.pages < 1) or (args.ads is not None and args.ads < 1) or args.start_page < 1 or not math.isfinite(args.delay) or args.delay < 1:
        parser.error("--pages, --ads and --start-page must be >= 1, and --delay must be >= 1 second")
    if args.output_dir and args.output_dir.resolve() == (PROJECT_DIR / "data" / "raw" / "baseline_2026-10-01").resolve():
        parser.error("The preserved baseline cannot be used as an output directory")
    if args.url:
        parsed = urlsplit(args.url)
        if parsed.scheme != "https" or parsed.hostname not in {"www.pakwheels.com", "pakwheels.com"} or not AD_PATH.fullmatch(parsed.path):
            parser.error("--url must be a PakWheels car advertisement URL")
    if args.sampling_plan and (args.pages is not None or args.start_page != 1):
        parser.error("Set max_pages and start_page in the sampling plan, not CLI page options")
    try:
        if args.sampling_plan:
            if args.output_dir is None:
                parser.error("--sampling-plan requires a separate --output-dir")
            searches = load_plan(args.sampling_plan)
            budget = args.ads or sum(spec.max_detail_requests for spec in searches)
        else:
            budget = args.ads or 10
            searches = (SearchSpec(
                "single" if args.url else "general", SEARCH_URL, None, None,
                1 if args.url else budget, 1 if args.url else budget,
                args.pages or 1, args.start_page,
            ),)
        run_collection(CollectionSettings(
            searches=searches, output_dir=args.output_dir or DATA_DIR,
            max_detail_requests=budget, delay=args.delay, contact=args.contact,
            refresh=args.refresh, cumulative_targets=bool(args.sampling_plan), single_url=args.url,
        ), sys.modules[__name__])
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
