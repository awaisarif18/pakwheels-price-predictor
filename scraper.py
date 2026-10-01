"""Small, sequential PakWheels research collector (use only with authorized access).

Install: pip install requests beautifulsoup4 pandas lxml
Try parser offline: python scraper.py --self-test
Try one permitted ad: python scraper.py --url 'https://www.pakwheels.com/used-cars/...'
Try limited search: python scraper.py --pages 1 --ads 10 --delay 5

The script never solves CAPTCHAs or circumvents access restrictions. It records
incomplete rows in pakwheels_raw.csv and complete rows in pakwheels_clean.csv.
"""

import argparse
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pandas as pd
import requests
from bs4 import BeautifulSoup

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
]

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


def load_existing():
    if not RAW_FILE.exists():
        return {}
    previous = pd.read_csv(RAW_FILE, dtype={"listing_id": "string"})
    if "source_url" not in previous.columns:
        return {}
    previous = previous.where(pd.notna(previous), None)
    return {str(row["source_url"]): row for row in previous.to_dict("records")}


def save_csv(records):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(records.values(), columns=COLUMNS)
    df.to_csv(RAW_FILE, index=False)
    clean = df[df["parse_status"] == "complete"].copy()
    clean.to_csv(CLEAN_FILE, index=False)
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
    parser.add_argument("--pages", type=int, default=1, help="Search pages to examine (default: 1)")
    parser.add_argument("--ads", type=int, default=10, help="Maximum listing URLs per run (default: 10)")
    parser.add_argument("--delay", type=float, default=5, help="Seconds between HTTP requests (default: 5)")
    parser.add_argument("--url", type=str, help="Test one specific permitted car listing URL")
    parser.add_argument("--contact", default="your-email@example.com", help="Research collector contact address")
    parser.add_argument("--self-test", action="store_true", help="Run parser tests without network")
    args = parser.parse_args()

    if args.self_test:
        run_self_test()
        return
    if args.pages < 1 or args.ads < 1 or args.delay < 1:
        parser.error("--pages and --ads must be >= 1, and --delay must be >= 1 second")
    if args.url:
        parsed = urlsplit(args.url)
        if parsed.scheme != "https" or parsed.hostname not in {"www.pakwheels.com", "pakwheels.com"} or not AD_PATH.fullmatch(parsed.path):
            parser.error("--url must be a PakWheels car advertisement URL")

    session = requests.Session()
    session.headers.update({
        "User-Agent": f"CarPriceResearch/0.2 (contact: {args.contact})",
        "Accept": "text/html,application/xhtml+xml",
    })
    records = load_existing()
    links = [args.url] if args.url else []
    try:
        if not args.url:
            discovered = dict()
            for page in range(1, args.pages + 1):
                search_url = SEARCH_URL.format(page=page)
                print(f"[SEARCH] Page {page}: {search_url}")
                html = fetch_page(session, search_url, args.delay)
                found = listing_links(html)
                print(f"[SEARCH] Found {len(found)} listing links")
                if not found:
                    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
                    (DEBUG_DIR / f"search_page_{page}.html").write_text(html, encoding="utf-8")
                    print(f"[DEBUG] Saved {DEBUG_DIR / f'search_page_{page}.html'}")
                    break
                for link in found:
                    discovered[link] = None
                if len(discovered) >= args.ads:
                    break
            links = list(discovered)[:args.ads]

        for number, link in enumerate(links[:args.ads], 1):
            if link in records and records[link].get("parse_status") == "complete":
                print(f"[{number}/{len(links)}] Already saved: {link}")
                continue
            print(f"[{number}/{len(links)}] Fetching: {link}")
            try:
                html = fetch_page(session, link, args.delay)
            except AccessRestricted:
                raise
            except requests.RequestException as exc:
                print(f"[REQUEST ERROR] {exc}")
                continue

            row, preview = parse_car(html, link)
            records[link] = row
            if row["parse_status"] == "complete":
                print(
                    f"[SUCCESS] {row['car_title']} | PKR {row['price_pkr']:,} | "
                    f"{row['mileage_km']:,} km"
                )
            else:
                print(f"[INCOMPLETE] Missing: {row['missing_fields']}")
                save_debug(html, link, row, preview)
                print(f"[DEBUG] Saved HTML and text sample under {DEBUG_DIR}/")
            total, complete = save_csv(records)  # Preserve results as the crawl proceeds.
            print(f"[CSV] {complete} clean rows / {total} total rows")

    except AccessRestricted as exc:
        print(f"[STOP] {exc}")
    except requests.RequestException as exc:
        print(f"[STOP] Network or HTTP error: {exc}")
    finally:
        total, complete = save_csv(records)
        session.close()
        print(f"[DONE] {CLEAN_FILE}: {complete} complete records")
        print(f"[DONE] {RAW_FILE}: {total} total records (including incomplete)")


if __name__ == "__main__":
    main()
