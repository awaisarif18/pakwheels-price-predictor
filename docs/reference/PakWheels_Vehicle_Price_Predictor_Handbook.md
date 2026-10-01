# Pakistan Vehicle Price Prediction System

## Project handbook: collection, cleaning, machine learning, and application plan

**Prepared:** 1 October 2026  
**Application:** One application with separate car and motorcycle asking-price predictors  
**Current milestone:** The user has successfully run the car scraper and generated raw and cleaned data.  
**Immediate next step:** Audit that sample, add reliable vehicle-name normalization, and validate a motorcycle parser before collecting at scale.

This file consolidates the discussion, preserves the actual previously supplied `scraper.py`, and records the next development steps. Planning numbers are engineering targets, not guarantees of model quality. The bike priority order comes from the user; it is not presented as a verified national sales or ownership ranking.

## Contents

1. [Goal, scope, and current status](#1-goal-scope-and-current-status)
2. [Access and private review](#2-access-and-private-review)
3. [Windows setup and dependencies](#3-windows-setup-and-dependencies)
4. [How the working car scraper works](#4-how-the-working-car-scraper-works)
5. [Complete working car scraper](#5-complete-working-car-scraper)
6. [Running the scraper and reading its output](#6-running-the-scraper-and-reading-its-output)
7. [Why the original scraper skipped listings](#7-why-the-original-scraper-skipped-listings)
8. [Known limits and upgrades before scaling](#8-known-limits-and-upgrades-before-scaling)
9. [Dataset size and sampling plan](#9-dataset-size-and-sampling-plan)
10. [Motorcycle scope and priority](#10-motorcycle-scope-and-priority)
11. [Motorcycle scraper implementation plan](#11-motorcycle-scraper-implementation-plan)
12. [Bike-name normalization code](#12-bike-name-normalization-code)
13. [Car-name normalization](#13-car-name-normalization)
14. [Target data schemas](#14-target-data-schemas)
15. [Cleaning and quality checks](#15-cleaning-and-quality-checks)
16. [Training two predictors](#16-training-two-predictors)
17. [Evaluation, leakage, and learning curves](#17-evaluation-leakage-and-learning-curves)
18. [One application, two models](#18-one-application-two-models)
19. [Repository structure and reproducibility](#19-repository-structure-and-reproducibility)
20. [Development roadmap and completion criteria](#20-development-roadmap-and-completion-criteria)
21. [Troubleshooting](#21-troubleshooting)
22. [Sources and handover notes](#22-sources-and-handover-notes)

## 1. Goal, scope, and current status

Build a **Pakistan Vehicle Price Prediction System** that estimates advertised asking prices in **PKR**:

- A car model trained on car advertisements.
- A motorcycle model trained on motorcycle advertisements.
- One Flask application that selects the correct model and feature schema.
- A private demonstration to the PakWheels contact before public release.

The intended outcome is an end-to-end ML project: data ingestion, parsing, normalization, quality checks, model comparison, evaluation, a usable interface, and reproducible artifacts.

| Component | Current status | What this means |
|---|---|---|
| Car URL discovery and detail scraping | User reports successful execution | A small working collection path exists on the user's connection |
| `pakwheels_raw.csv` and `pakwheels_clean.csv` | User reports generated successfully | Parser-complete data exists; ML readiness still needs an audit |
| Car make/model/variant normalization | Planned | Current scraper preserves `car_title`, not separate identity features |
| Bike scraper | Planned; live parsing unverified | A separate parser must be checked against actual returned motorcycle HTML |
| Bike coverage | Six initial models selected | The first bike release can have a clear, manageable scope |
| Training, evaluation, and model artifacts | Planned | No accuracy results or trained models are claimed in this handbook |
| Application and publishing | Planned | Review privately before publishing |

**Predict asking price, not guaranteed resale value.** An advertisement's listed price is not necessarily the agreed transaction price. Use labels such as **Estimated Asking Price** or **Estimated Listing Price**.

The original Indian-market project mentioned earlier cannot be converted simply by replacing its CSV. Retrain on Pakistani data, synchronize the backend inputs with the new feature schema, and replace any Indian currency presentation with PKR. Its original repository URL is not available in the supplied conversation, so repository-specific details should be checked when that code is opened.

## 2. Access and private review

The user reports that their PakWheels contact permitted scraping and building an application, with a request to see the application before it is published. This handbook proceeds on that reported authorization; it does not ask the user to obtain the same permission again.

Keep the prototype private through the requested review. For a larger crawl or commercial release, record the agreed request volume, data-use scope, attribution, ownership of project code, and publication conditions so the collaboration is clear.

The collector uses ordinary sequential requests with a configurable delay. If it encounters access denial or a challenge page, stop and resolve the access method with the contact. It does not need proxy rotation, CAPTCHA solving, or access-control bypasses. Collect vehicle attributes rather than seller phone numbers or other unnecessary personal data.

## 3. Windows setup and dependencies

Use the existing project folder and environment if they already work. Do not recreate the environment merely because this handbook includes first-time setup instructions.

### First-time setup

In Windows PowerShell:

```powershell
mkdir pakwheels-price-predictor
cd pakwheels-price-predictor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

For the user's existing folder:

```powershell
Set-Location "D:\Coding Projects\pakwheels-price-predictor"
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, either use the environment's Python directly or, where local policy allows it, set a process-only execution policy:

```powershell
.\.venv\Scripts\python.exe scraper.py --self-test
```

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Scraper dependencies: `requirements.txt`

```text
requests>=2.32,<3
beautifulsoup4>=4.12,<5
pandas>=3,<4
lxml>=5
```

These are proposed dependency ranges, not a tested lockfile. The old `pandas>=2,<3` upper bound was conservative; it is not inherently required by this scraper's basic CSV and DataFrame operations. The user identified pandas 3.0.6 in their environment. If that is the version you install and validate, pin it in the lockfile. Do not rely on the earlier unverified release-date statement.

Use a Python version supported by every dependency you install; Python 3.12 is a reasonable starting environment to validate. Check the current package metadata if installation reports incompatible Python requirements. pandas' official installation guidance is linked in Section 22.

```powershell
python --version
python -m pip install -r requirements.txt
python -m pip check
python -c "import pandas as pd; print(pd.__version__)"
python scraper.py --self-test
python -m pip freeze > requirements-lock.txt
```

Use `requirements-lock.txt` to reproduce the tested environment later. Keep the human-maintained dependency ranges separately.

### ML and application dependencies: later phase

```powershell
python -m pip install catboost scikit-learn matplotlib flask
python -m pip check
python -m pip freeze > requirements-lock.txt
```

Do this when starting training and application work. Confirm wheel availability and compatibility on the actual operating system and Python version.

## 4. How the working car scraper works

The working approach separates URL discovery from detail-page parsing.

1. Request an approved car search page.
2. Find anchors whose paths match individual car advertisements.
3. Normalize URLs and remove duplicates while preserving discovery order.
4. Visit each selected advertisement sequentially.
5. Locate its `h1` and extract text following the heading.
6. Exclude common seller/recommendation sections and parse vehicle attributes.
7. Convert Pakistani price units to total PKR.
8. Save every parsed record, including incomplete ones.
9. Write parser-complete records into the clean CSV.
10. Save diagnostic HTML and text for incomplete records.

| Detail | Current implementation |
|---|---|
| Car search URL | `https://www.pakwheels.com/used-cars/search/-/?page={page}` |
| Car listing pattern | `/used-cars/...-for-sale-in-...-<listing_id>` |
| HTTP libraries | `requests.Session()` and BeautifulSoup with `lxml` |
| Default limits | One search page, ten selected advertisement URLs, five-second delay |
| Price formats | PKR totals, lac/lakh, crore/cr, million/mn |
| Essential fields | Title, price, year, mileage |
| Optional fields | Fuel, transmission, engine capacity |
| City and ID | Derived from the advertisement URL |
| Checkpoint | CSV written after each parsed advertisement |
| Resume behavior | Already-complete URLs in the existing raw CSV are skipped |

Price normalization examples:

| Website value | Stored `price_pkr` |
|---|---:|
| `PKR 23.5 lacs` | 2,350,000 |
| `PKR 1.2 crore` | 12,000,000 |
| `PKR 4,500,000` | 4,500,000 |

The saved clean file means **complete according to this parser's checks**. It does not mean fully normalized, reviewed, or ready for model training.

## 5. Complete working car scraper

Save the following block as **`scraper.py`** in the project root. It is the full previously supplied file recovered for this handbook, rather than a reconstructed replacement. The user reports this version successfully scraped and cleaned car data.

The offline self-tests use small synthetic HTML fixtures. Passing them checks the included examples; it does not prove the current website markup is fully covered.

```python
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
RAW_FILE = Path("pakwheels_raw.csv")
CLEAN_FILE = Path("pakwheels_clean.csv")
DEBUG_DIR = Path("debug_pages")

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
    DEBUG_DIR.mkdir(exist_ok=True)
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
                    DEBUG_DIR.mkdir(exist_ok=True)
                    (DEBUG_DIR / f"search_page_{page}.html").write_text(html, encoding="utf-8")
                    print(f"[DEBUG] Saved debug_pages/search_page_{page}.html")
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
```

## 6. Running the scraper and reading its output

### Offline parser test

```powershell
python scraper.py --self-test
```

Expected message:

```text
2 offline parser self-tests passed. (Live access not tested.)
```

### Small live sample

```powershell
python scraper.py --pages 1 --ads 10 --delay 5 --contact "your-real-email@example.com"
```

Replace the example contact address with your own. The command selects at most ten URLs, not necessarily ten newly saved records; some may already exist or be incomplete.

### Test a specific advertisement

Copy a current authorized car advertisement URL and replace the placeholder:

```powershell
python scraper.py --url "PASTE_CURRENT_PAKWHEELS_CAR_LISTING_URL_HERE" --delay 5 --contact "your-real-email@example.com"
```

The placeholder is intentionally not a fabricated live listing. `--url` accepts only a matching PakWheels HTTPS car advertisement.

### Outputs

| File or folder | Purpose |
|---|---|
| `pakwheels_raw.csv` | Parsed rows, including incomplete ones, plus diagnostic status |
| `pakwheels_clean.csv` | Rows with title, price, year, and mileage present |
| `debug_pages/failed_<id>.html` | Returned HTML for an incomplete listing |
| `debug_pages/failed_<id>.txt` | Missing fields and a visible-text preview |
| `debug_pages/search_page_<n>.html` | Search HTML saved when no advertisement links were found |

Files are created relative to the directory from which you run Python. Keep a consistent working directory so resume behavior uses the intended CSV.

The present file stores one row per canonical URL. It is a snapshot collector: it skips complete saved rows and does not refresh price history. Later repeated collection needs a history table or dated snapshots.

## 7. Why the original scraper skipped listings

The first parser returned `None` when price, year, or mileage did not match. That produced the same generic message for different failures:

```python
if not (price_match and years and mileage_match):
    return None
```

Its price regex required at least five digits after `PKR` and searched only a short character window. A price such as `PKR 23.5 lacs` did not fit. Mileage or title position could also be missed.

The replacement improved diagnosis and retention:

- Pakistani unit conversion instead of accepting only full numeric prices.
- Wider text windows and a fallback price match.
- Named missing fields instead of silently discarding an advertisement.
- Incomplete records in the raw CSV.
- Failed HTML and text saved for inspection.
- Ordered URL deduplication instead of alphabetically sorting links.
- Incremental saves and reuse of already-complete records.

The general debugging rule is to inspect what the Python client actually received. Browser-rendered content, indexed search text, and the response returned to `requests` can differ.

## 8. Known limits and upgrades before scaling

Preserve the working file as a baseline. Make changes in a branch and test them against saved HTML before replacing it.

| Limitation | Consequence | Planned improvement |
|---|---|---|
| Visible-text regexes and character windows | Can miss fields or accidentally match unrelated text | Prefer verified detail-section selectors or valid structured data, with scoped fallbacks |
| Price search takes the first match in its window | Nearby non-listing prices may be captured | Scope to the main asking-price element; retain price provenance |
| Year falls back to nearby text | An unrelated year could be selected | Prefer labelled model year and record extraction source |
| Optional fields are not required | Clean rows can lack valuable ML features | Report field coverage and define model-specific required fields |
| No separate make/model/variant | Raw title is insufficient for controlled user inputs | Add catalogue-based normalization |
| No CAPTCHA/challenge detection for HTTP 200 | A challenge may be recorded as missing listing data | Recognize verified challenge markup and stop; avoid broad keyword-only detection |
| Always starts at page 1 | Repeated runs may revisit the same head of the catalogue | Add a tested start-page option and a queued URL manifest |
| Already-saved URLs count toward `--ads` | A run may add fewer new rows than expected | Distinguish selected URLs, attempted requests, and newly saved rows |
| One row per URL | No history of changes | Keep separate listing and snapshot tables |
| Deduplication by URL only | Reposted vehicles can still duplicate training examples | Investigate repost groups before splitting |
| Entire CSV rewritten per record | Increasing overhead at larger volumes | Use SQLite/upserts or append-only checkpoints plus exports |
| Network-error listings are only logged | No durable retry queue | Record failed URLs and retry ordinary transient errors within limits |

### Minimal pagination extension

The current CLI has no `--start-page`. After validating this change, add:

```python
parser.add_argument("--start-page", type=int, default=1)
```

Validate it alongside the other arguments:

```python
if args.start_page < 1:
    parser.error("--start-page must be >= 1")
```

Replace the existing page loop:

```python
for page in range(args.start_page, args.start_page + args.pages):
    # Existing loop body stays here.
    ...
```

This is a patch sketch, not a second complete scraper. Search result positions can move as new advertisements arrive. A saved URL queue and deduplication remain necessary.

The current code stops on HTTP 401, 403, or 429 but does **not** fully detect HTTP-200 challenge pages. Do not interpret an empty extraction from such a page as a normal empty catalogue.

## 9. Dataset size and sampling plan

There is no universal minimum number of advertisements for regression. Coverage, feature quality, duplicates, market freshness, and acceptable error determine whether a dataset is sufficient.

The earlier planning targets were:

| Stage | Unique cleaned car advertisements | Unique cleaned bike advertisements |
|---|---:|---:|
| Initial experiment | 3,000–5,000 | 2,000–3,000 |
| Serious prototype | 15,000–25,000 | 7,000–12,000 |
| Broader coverage, if justified | 50,000+ | 20,000+ |

**Working milestone:** 20,000 cars and 10,000 bikes. These are expandable targets, not minimum requirements or an instruction to collect them all immediately. With only six bike families in the first release, good results may be possible before 10,000; use measured errors to decide.

Count unique usable advertisements after deduplication, not raw requests or repeated observations of the same advertisement. Reposted copies can still inflate apparent sample size.

### Cars

Start with practical scope such as Suzuki, Toyota, Honda, KIA, and Hyundai, across Lahore, Karachi, Islamabad, Rawalpindi, and Faisalabad. The earlier year window was 2005–2026. These are proposed collection strata; adjust them to actual marketplace coverage and the form's supported scope.

Sample across:

- Make, model, and variant.
- Model year or age band.
- Listing city and region.
- Mileage band.
- Price bracket, inspected as a coverage measure rather than a prediction input.
- Transmission, fuel, and local/imported assembly where reliably available.

Do not claim that a 20,000-row dataset provides reliable estimates for every imported or rare vehicle. A category with only three examples still has weak evidence.

### Collection controls

Maintain a manifest containing the approved search URL, vehicle type, intended model/city/year stratum, run ID, date, page range, request count, parser version, and collection outcome. Verify actual filter URLs rather than inventing them from model names.

The five-second default alone implies at least **41.7 hours for 30,000 detail requests**, excluding search requests, response time, failures, and pauses. Plan resumable runs; do not assume a large crawl will finish in one session.

Inspect a small random sample from every batch, including rare models, unusually low/high prices, missing fields, and different city/year strata. Ten records per hundred is a possible initial review policy, not a statistical guarantee. Measure error rates and adapt the review size.

## 10. Motorcycle scope and priority

The user supplied this order for common motorcycles to prioritize in Pakistan. Preserve the order as the project's collection priority:

| Priority | Canonical make | Canonical model | User's wording | Initial clean-record target |
|---:|---|---|---|---:|
| 1 | Honda | CD 70 | Honda CD70 | 500 |
| 2 | Honda | CG 125 | Honda CG125 | 500 |
| 3 | Honda | CB 150F | Honda CB150 F | 500 |
| 4 | Suzuki | GS 150 | Suzuki GS 150 | 500 |
| 5 | Suzuki | GR 150 | Suzuki GR 150 | 500 |
| 6 | Yamaha | YBR 125 | Yahamah YBR 125 | 500 |
| | | | **Initial target** | **3,000** |

The quotas are an initial coverage goal, not asserted marketplace availability. If a family has few current listings, collect what is available and document the gap. Do not create synthetic advertisements to meet a quota.

Normalize the spelling **Yahamah → Yamaha**. Retain the original title in the raw data so every normalization can be audited.

### Why begin with these six?

This creates a useful bounded product: one shared bike model trained across six supported families, with make/model features distinguishing them. It does not require six separately trained predictors.

CD 70 and CG 125 may dominate the available listings. Collecting only their first search pages would leave little evidence for the other four families. Initial similar-sized quotas support comparison across the six. Later allocation should respond to observed error, availability, and the application's intended users.

### Variants must remain distinct

Do not automatically merge similar names:

- CD 70 and CD 70 Dream.
- CG 125 and named special/self-start/other variants.
- GS 150 and GS 150 SE.
- YBR 125 and YBR 125G.

Whether a variant belongs in the first release is a catalogue decision. Keep its variant label and validate its semantics before including it. A normalized family name is not permission to discard variant information.

Start with years actually represented in usable data. Do not promise reliable predictions for every old or future model year merely because the model family is supported.

### Expansion toward 10,000 bikes

After the 3,000-record pilot, use per-family learning curves and errors to decide where additional rows help. A possible balanced coverage checkpoint is around 1,000 usable listings per family, where available; the remaining budget can follow errors and real demand. Preserve an evaluation sample that resembles deployment traffic or report both macro averages across families and observed-distribution averages.

## 11. Motorcycle scraper implementation plan

**Status:** This section describes the next module. No live-tested bike scraper is included or claimed.

Bike advertisements use the `/used-bikes/` marketplace namespace, but their URL patterns, search pagination, and detail markup must be checked from actual motorcycle responses before selectors or path regexes are finalized.

### Reuse from the car collector

- Session, identifiable user agent, delay, timeout, and stop behavior.
- Ordered URL discovery and canonicalization.
- PKR/lac/crore normalization.
- Raw/clean outputs and diagnostics.
- Incremental persistence and duplicate detection.

### Keep separate

- Bike search URL templates and individual listing URL validation.
- Main detail-section selectors.
- Bike title, make, model, and variant extraction.
- Registration, assembly, engine type/displacement, and mileage extraction.
- Bike-specific quality rules and supported-model checks.

Do not replace every `used-cars` string with `used-bikes` and assume the parser is correct. Do not assign engine capacity merely from model-name digits; prefer verified specification fields and record any catalogue-derived values separately.

### First validation pass

1. Save returned HTML for at least one current advertisement from each of the six selected families.
2. Add examples with differing price formats, zero/missing mileage, and variants where available.
3. Identify the actual main listing container and labelled specifications.
4. Extract the advertised price from that container, excluding related advertisements.
5. Verify model year, kilometres, registration, assembly, and engine attributes against the visible advertisement.
6. Add regression fixtures from the permitted saved HTML, omitting unnecessary seller data.
7. Generate `bikes_raw.csv` and a parser-complete `bikes_clean.csv`.
8. Add name normalization and stricter ML quality checks.
9. Run a small live batch and manually review it before raising collection limits.

Suggested signature:

```python
def parse_bike(html, url):
    """Return a bike record plus diagnostics using verified motorcycle markup."""
    # Implement after inspecting saved motorcycle HTML.
    raise NotImplementedError("Motorcycle detail parser still needs live HTML validation")
```

This is an interface placeholder, not runnable bike extraction.

## 12. Bike-name normalization code

The following standalone helper normalizes the six chosen families from titles. Save it as **`preprocessing/normalize_bike_names.py`** after creating that folder. It is a conservative title helper, not a complete vehicle catalogue or a replacement for structured fields.

It preserves trailing variant text and requires make context. Unknown or ambiguous identities remain flagged rather than guessed. Named variants should be reviewed against the catalogue before deciding first-release support.

```python
"""Conservative title normalization for the six initial motorcycle families."""

import re

CATALOGUE = [
    ("Honda", "CD 70", r"\bcd\s*70\b"),
    ("Honda", "CG 125", r"\bcg\s*125\b"),
    ("Honda", "CB 150F", r"\bcb\s*150\s*f\b"),
    ("Suzuki", "GS 150", r"\bgs\s*150\b"),
    ("Suzuki", "GR 150", r"\bgr\s*150\b"),
    # No final word boundary here: YBR125G must retain G as a variant.
    ("Yamaha", "YBR 125", r"\bybr\s*125(?=\b|g\b)"),
]
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def normalize_bike_title(title, known_make=None):
    original = "" if title is None else str(title)
    text = re.sub(r"\s+", " ", original).strip()
    text = re.sub(r"\byahamah\b", "Yamaha", text, flags=re.I)
    text = text.replace("-", " ")
    years = YEAR_RE.findall(text)
    name_text = YEAR_RE.sub(" ", text)
    matches = []

    for make, model, pattern in CATALOGUE:
        model_match = re.search(pattern, name_text, flags=re.I)
        make_present = re.search(rf"\b{re.escape(make)}\b", name_text, re.I)
        make_known = str(known_make or "").casefold() == make.casefold()
        if model_match and (make_present or make_known):
            matches.append((make, model, model_match))

    if len(matches) != 1:
        return {
            "original_title": original,
            "make": None,
            "model": None,
            "variant_raw": None,
            "title_year": int(years[0]) if len(years) == 1 else None,
            "normalization_status": "ambiguous" if matches else "unmatched",
        }

    make, model, model_match = matches[0]
    remainder = name_text[:model_match.start()] + " " + name_text[model_match.end():]
    remainder = re.sub(rf"\b{re.escape(make)}\b", " ", remainder, flags=re.I)
    remainder = re.sub(r"\bfor\s+sale\b", " ", remainder, flags=re.I)
    remainder = re.sub(r"\s+", " ", remainder).strip(" |,:;/")
    return {
        "original_title": original,
        "make": make,
        "model": model,
        "variant_raw": remainder or None,
        "title_year": int(years[0]) if len(years) == 1 else None,
        "normalization_status": "matched_variant_review" if remainder else "matched",
    }


if __name__ == "__main__":
    examples = [
        ("Honda CD70 2022", "Honda", "CD 70", None),
        ("Honda CG125 2021", "Honda", "CG 125", None),
        ("Honda CB150 F 2020", "Honda", "CB 150F", None),
        ("Suzuki GS 150 2019", "Suzuki", "GS 150", None),
        ("Suzuki GR150 2023", "Suzuki", "GR 150", None),
        ("Yahamah YBR 125 2022", "Yamaha", "YBR 125", None),
        ("Yamaha YBR125G 2022", "Yamaha", "YBR 125", "G"),
        ("Suzuki GS150 SE 2021", "Suzuki", "GS 150", "SE"),
        ("Honda CD70 Dream 2022", "Honda", "CD 70", "Dream"),
    ]
    for title, make, model, variant in examples:
        row = normalize_bike_title(title)
        assert (row["make"], row["model"], row["variant_raw"]) == (make, model, variant), row
    assert normalize_bike_title("YBR 125 2022")["normalization_status"] == "unmatched"
    assert normalize_bike_title("Honda CD70 and CG125 2022")["normalization_status"] == "ambiguous"
    print("11 offline bike-name normalization checks passed.")
```

Run:

```powershell
python preprocessing/normalize_bike_names.py
```

Keep `title_year` separate from a verified labelled year. Listings with city text or descriptive wording in the title may leave that wording in `variant_raw`; review it rather than turning it into a canonical variant automatically. Missing variant text means unknown/unspecified, not necessarily a verified standard trim.

## 13. Car-name normalization

Train one general car regressor initially, with make/model/variant as categorical features. There is no need to train a separate model for every car.

For a title such as `Honda Civic Oriel 1.8 i-VTEC CVT 2019`, the desired identity fields are:

| Field | Intended normalized value |
|---|---|
| Make | Honda |
| Model | Civic |
| Variant | Oriel 1.8 i-VTEC CVT |
| Model year | 2019 |

Engine capacity and transmission should come from verified fields or documented catalogue mappings; do not silently infer them from ambiguous words in a title.

### Catalogue approach

1. Preserve `car_title` and any structured identity fields from the source.
2. Normalize whitespace, punctuation, case, and known spelling aliases.
3. Match make/model names using a maintained catalogue; prefer the longest valid model-name match.
4. Retain full residual variant wording until a variant mapping is verified.
5. Store normalization status and catalogue version.
6. Put unmatched and ambiguous names into a review queue.

Do not assume the first token is always the make and the second token is always the model. Multiword makes/models and special naming patterns can break that rule.

Do not collapse Oriel, RS Turbo, GLi, Grande, VXL AGS, or other materially different variants into a generic vehicle merely to reduce the number of categories. Equivalent aliases should merge only when the catalogue confirms equivalence.

## 14. Target data schemas

Add a feature only when it can be reliably extracted and the user can provide the same information at prediction time.

### Identity, inputs, and target

| Column | Cars | Bikes | Role |
|---|---|---|---|
| `vehicle_type` | `car` | `bike` | Routing and metadata |
| `make` | Yes | Yes | Categorical input |
| `model` | Yes | Yes | Categorical input |
| `variant` | If reliable | If reliable | Categorical input |
| `year` | Yes | Yes | Numerical input |
| `mileage_km` | Yes | Yes | Numerical input |
| `engine_cc` | Where applicable | Where applicable | Numerical input |
| `fuel` | Where available | Optional; includes electric cases | Categorical input |
| `transmission` | Where available | Only if informative and reliable | Categorical input |
| `assembly` | Local/imported if verified | Local/imported if verified | Categorical input |
| `listing_city` | Yes | Yes | Categorical input |
| `registration_city` | If reliable | If reliable | Categorical input |
| `body_type` | If reliable | Usually unnecessary initially | Categorical input |
| `price_pkr` | Yes | Yes | **Regression target; never an input** |

Do not invent `engine_cc=0` for an electric vehicle. Preserve non-applicability and use suitable fuel/powertrain information where coverage supports it.

### Provenance and QA metadata

| Column | Purpose | Feed to first model? |
|---|---|---|
| `listing_id` | Deduplication and source traceability | No |
| `source_url` | Audit link | No |
| `car_title` / `bike_title` | Preserve original wording | No in the structured first model |
| `collected_at` | Snapshot time, UTC ISO format | Keep for evaluation and freshness; not automatically a feature |
| `first_seen_at` / `last_seen_at` | Repeated-collection history | No initially |
| `posted_at` | Listing date if reliably extractable | Useful for temporal evaluation |
| `crawl_run_id` | Collection manifest link | No |
| `parser_version` | Reproduce extraction behavior | No |
| `catalogue_version` | Reproduce name mappings | No |
| `normalization_status` | Identity QA | Filter/review metadata |
| `parse_status` / `missing_fields` | Extraction diagnostics | No |
| `quality_flags` | Outlier/missingness review | QA metadata |
| `vehicle_group_id` | Suspected repost grouping | Split control, not model input |

Collection time is not the vehicle's manufacturing year or necessarily the advertisement's posting time. A fresh scrape can include an older listing.

## 15. Cleaning and quality checks

### Raw data must remain recoverable

Keep immutable dated raw snapshots or an append-only history. Write normalized training candidates into a separate processed location. Avoid manually editing the only raw CSV.

### Recommended checks

1. Parse price units without removing meaningful decimal notation.
2. Ensure `price_pkr` is positive and recorded as a complete PKR amount.
3. Convert mileage/year/engine capacity to numeric values while preserving nulls.
4. Accept zero mileage as a possible value; inspect context rather than rejecting it as falsey.
5. Flag implausible year, mileage, engine, or price values for review.
6. Normalize make/model/variant/city consistently and retain the original text.
7. Deduplicate advertisement IDs within vehicle type.
8. Investigate probable reposts and group them before evaluation splitting.
9. Track missingness and extraction success by model, city, and year.
10. Record exclusions and review reasons so cleaning is reproducible.

A bike advertised at a very high price may be a typo, unusual condition, a bundle, or a legitimate outlier. Review it against its source and comparables; do not delete every expensive row automatically. No fixed universal car or bike price cutoff is prescribed here.

### Missing inputs

- Preserve missing values in raw data.
- Define which fields are mandatory for each model version.
- Use explicit string placeholders for categorical missing values in CatBoost.
- Fit numeric imputation values on training data only, if imputation is used.
- Carry the same preprocessing into inference.
- Track the effect of complete-case filtering; missing mileage can bias which listings remain.

Dropping duplicates by make/model/year/mileage alone can remove different legitimate vehicles. Exact listing ID duplication is straightforward; inferred same-vehicle grouping needs evidence and review.

### Dataset audit report

Produce row counts, unique IDs, date range, make/model/year/city distributions, variant coverage, missing-field rates, parsing success, exclusion counts, flagged outliers, and examples of unmatched names. This report decides whether to collect more data or improve extraction first.

## 16. Training two predictors

Use independent feature schemas, preprocessing, evaluation, and saved artifacts for cars and motorcycles.

| Predictor | Dataset | Candidate artifact | Scope |
|---|---|---|---|
| Cars | `data/processed/cars_clean.csv` | `models/cars_model.cbm` | Initially supported car families with adequate evidence |
| Bikes | `data/processed/bikes_clean.csv` | `models/bikes_model.cbm` | The six initial bike families and reviewed variants |

### Models to compare

| Candidate | Why include it |
|---|---|
| Median-price baseline | Tests whether ML improves on simple comparable-group prices |
| Random Forest Regressor | A useful tabular benchmark and continuity with the earlier project |
| CatBoost Regressor | Candidate that handles mixed numerical and categorical inputs directly |

CatBoost is a candidate to validate, not a guaranteed winner. Its native categorical-feature support is documented by its maintainers; see Section 22.

For the median baseline, compute group medians **only on training data**, with fallbacks such as make/model/year, then make/model, then make, then the global training median. Tune minimum group support on validation data.

Random Forest needs an appropriate encoded numerical feature matrix. Fit its encoders, imputers, and feature transformations on training data only. Use unknown-category handling for validation, test, and inference.

### CatBoost implementation guidance

- Categorical columns: make, model, reviewed variant, city, and other reliable categorical inputs.
- Numeric columns: year or age, mileage, engine capacity where applicable.
- Target: PKR asking price.
- Convert categorical missing values to an explicit string such as `__MISSING__`.
- Select hyperparameters and early stopping using validation data.
- Save the feature order, categorical fields, preprocessing rules, and catalogue version with the model.
- Compare raw-PKR and log-price targets if useful; evaluate both after converting predictions back to PKR. A log target does not automatically optimize PKR MAE, and exponentiating has its own bias considerations.

Avoid raw advertisement IDs and URLs as inputs. Do not include price-derived columns, leaked target encodings, or features unavailable in the application form.

### Sparse models and unfamiliar inputs

A shared model can learn patterns across related vehicles, but cannot establish reliability for a family/variant with almost no examples. Define supported scope from validation evidence and training support.

An initial sparse-category rule such as flagging fewer than 30 training examples can be tried as a diagnostic; it is not a universal confidence threshold. Pair counts with subgroup error and input-range checks.

For unsupported makes/models, unreviewed variants, or values well outside the training range, return an insufficient-data response or a clearly limited estimate according to a documented policy. Do not promise accurate extrapolation.

## 17. Evaluation, leakage, and learning curves

### Initial split

For an initial single-period experiment, use approximately:

| Split | Percentage | Use |
|---|---:|---|
| Training | 70% | Fit the models and preprocessing |
| Validation | 15% | Tune/select models and support rules |
| Test | 15% | Final untouched performance report |

Assign related snapshots/reposts to one split using a group identifier. These are proportions of independent groups where necessary; exact row proportions may vary.

### Chronological evaluation

After collecting over multiple dates, reserve newer advertisements/first-seen groups for a future-facing test. Prevent the same vehicle group from crossing into both train and test. `collected_at` alone is not enough if old listings are repeatedly scraped into later snapshots.

Use group-aware or temporal validation that matches the planned deployment question. Do not tune on the final test set.

### Metrics

| Metric | Interpretation |
|---|---|
| MAE in PKR | Average absolute difference between predicted and listed prices |
| Median absolute error | Typical absolute error, less affected by a few large misses |
| Median absolute percentage error | Median of `100 * abs(predicted - actual) / actual`, for positive actual prices |
| RMSE | More sensitive to large mistakes; optional companion metric |
| Error by family, variant, age, city, and price band | Reveals groups hidden by the aggregate score |
| Prediction interval coverage and width | Required if the interface shows a calibrated range |

An MAE of PKR 150,000 means an average absolute error of that amount. It does not mean every prediction is within PKR 150,000. Do not call a regression score “90% accuracy.”

Report cars and bikes separately because their price scales differ. For the six-bike scope, also report an equal-family macro average and the observed-sample weighted average. Show subgroup sample counts and uncertainty where feasible.

### Learning curves

For cars, compare nested training subsets around 3,000, 5,000, and 10,000 rows, then larger sizes if available. For bikes, begin with smaller subsets within the six-family scope. Keep validation/test groups fixed, maintain coverage, and repeat with a few seeds where appropriate.

Plot error against training size. If more data stops helping, investigate variant quality, outliers, missing inputs, stale prices, or model capacity before collecting thousands more advertisements.

### Price ranges

Do not label an arbitrary ±10% band as a confidence interval. Calibrate ranges using held-out residuals, quantile methods, or a documented interval method, and measure coverage on untouched data. If calibration is a separate step after tuning, reserve a calibration partition or use a method that respects data reuse and chronology.

Include observation date/model version in the result. Market drift can degrade a range calibrated on older data.

## 18. One application, two models

One Flask application can load both model bundles and route predictions according to a car/bike selector.

| User selection | Form behavior | Backend behavior |
|---|---|---|
| Car | Show supported car makes/models, reviewed variants, year, mileage, and reliable car features | Validate against car schema and run car preprocessing/model |
| Motorcycle | Initially show the six selected families and reviewed variants | Validate against bike schema and run bike preprocessing/model |

Each model bundle should include:

- The trained model.
- Feature schema and exact column order.
- Categorical/numeric field definitions.
- Preprocessing and catalogue version.
- Supported makes/models/variants and input ranges.
- Training-support summary and evaluation metrics.
- Calibration artifacts if showing a price range.
- Dataset date range, training date, and dependency lock reference.

### Inference sequence

1. Read vehicle type and validate the request.
2. Normalize inputs with the same catalogue used during training.
3. Reject unsupported identities or malformed values.
4. Select the model bundle and build the expected feature row.
5. Apply saved preprocessing, then predict.
6. Apply support/range checks and interval calibration if available.
7. Return an **Estimated Asking Price in PKR**, data/model date, and meaningful limitations.

The interface should use dropdowns constrained by supported catalogue entries so model/variant combinations are valid. Do not require users to enter technical pipeline details.

Comparable listings can be added later, using permitted current source data and clearly separated from the model estimate. City-specific behavior and the motorcycle scope can become useful parts of the private demonstration, subject to evidence from evaluation.

The earlier conversation suggested PakWheels has an existing car calculator. Verify the live product separately before making competitive claims; this handbook does not establish its current features or availability.

## 19. Repository structure and reproducibility

The structure below is the intended project layout, not a claim that all files have already been implemented:

```text
pakwheels-price-predictor/
  scraper.py                     # Preserved working car collector
  scrapers/
    common.py                    # Shared collection/persistence utilities
    car_scraper.py               # Refactored car adapter
    bike_scraper.py              # Verified motorcycle adapter
  preprocessing/
    clean_cars.py
    clean_bikes.py
    normalize_vehicle_names.py
    normalize_bike_names.py
  catalogues/
    cars.json
    bikes.json
  data/
    raw/
    processed/
    manifests/
  debug_pages/
  training/
    train_cars.py
    train_bikes.py
    evaluate.py
  models/
    cars_model.cbm
    cars_schema.json
    bikes_model.cbm
    bikes_schema.json
  reports/
    dataset_audit.md
    cars_metrics.json
    bikes_metrics.json
    learning_curves.png
  templates/
    index.html
  static/
    style.css
  app.py
  requirements.txt
  requirements-lock.txt
  README.md
```

Keep the currently working `scraper.py` until the refactor is verified. Do not remove it before the replacement produces equivalent results on regression fixtures.

Suggested `.gitignore` entries:

```gitignore
.venv/
__pycache__/
*.pyc
.env
data/raw/
data/processed/
debug_pages/
pakwheels_raw.csv
pakwheels_clean.csv
models/*.cbm
```

Store datasets/model artifacts in appropriate private versioned storage; record their hashes and locations in manifests. Excluding them from Git is not a backup strategy.

For each experiment record the Git commit, parser/catalogue version, dataset checksum, dependency lockfile, split/group policy, seed, feature schema, hyperparameters, metrics, and saved model location.

## 20. Development roadmap and completion criteria

| Phase | Work | Completion evidence |
|---|---|---|
| 0 — Preserve working baseline | Keep the successful scraper, CSV sample, and setup details | Offline tests pass in the user's environment; sample is recoverable |
| 1 — Audit cars | Review values and field coverage; investigate extraction mistakes | Audit report with examples, exclusions, and coverage gaps |
| 2 — Normalize identities | Add car catalogue and six-family bike mapping | Unknown/ambiguous queue; variants retained; regression checks |
| 3 — Validate bike parser | Inspect motorcycle HTML and implement a separate adapter | Representative live records verified across all six families |
| 4 — Collect pilot datasets | Aim for 3,000–5,000 cars and around 3,000 bikes where available | Deduplicated, reviewed datasets plus collection manifests |
| 5 — Train benchmarks | Median baseline, Random Forest, CatBoost | Same held-out groups; model comparison and subgroup errors |
| 6 — Analyze gaps | Learning curves, sparse families, outliers, missing features | A prioritized collection or parsing improvement list |
| 7 — Build application | Two schemas/models, support checks, PKR form/results | Valid inputs produce correct routing; unsupported inputs handled |
| 8 — Private demonstration | Prepare reproducible private build for contact review | Reviewable behavior and documented limits |
| 9 — Expand based on evidence | Work toward 20,000 cars/10,000 bikes if useful and within scope | Additional data improves measured error/coverage |
| 10 — Release and monitoring | Publish following the requested review; monitor data/model drift | Approved release, versioning, refresh policy, evaluation checks |

### Next coding session

- Audit the existing car CSV, rather than immediately increasing `--ads`.
- Confirm whether make/model/variant are available as structured fields in the actual response.
- Run the bike-name helper and begin a reviewed catalogue.
- Obtain current returned HTML examples for the six bike families.
- Implement and test `parse_bike()` against those examples.
- Add start-page/queue controls before large repeated runs.
- Define the first model's mandatory inputs and supported scope.

### Before claiming a predictor is ready

- Model beats the training-only comparable-price baseline on held-out groups.
- Per-model errors and sample counts are reported.
- Test results are untouched by tuning.
- Reposts/snapshots do not cross data splits.
- Training and inference use identical normalization and schemas.
- Unsupported variants and input ranges have defined behavior.
- A displayed price range has measured calibration/coverage.
- Outputs clearly say asking price and PKR.
- The private review requested by the contact is completed before public release.

## 21. Troubleshooting

| Symptom | Likely cause | What to inspect |
|---|---|---|
| Every advertisement incomplete | Markup mismatch, challenge response, price/mileage regex miss | Returned HTML and `missing_fields` |
| Search discovers no links | Wrong page URL, changed markup, empty results, access challenge | Saved search HTML and actual response |
| More pages but no new rows | Already-saved head listings count toward selected URL cap | Start-page/queue behavior and run counts |
| `ModuleNotFoundError` | Wrong interpreter or missing dependency | Active environment; use `python -m pip` |
| Output CSV appears missing | Different working directory | `Get-Location` and directory contents |
| Prices off by 100,000 or 10,000,000 | Unit-conversion error | Original price text and parser provenance |
| Fuel/transmission unexpectedly null | Position-dependent matching failed | Main detail HTML and labelled fields |
| Clean CSV has odd model names | Identity normalization incomplete | Raw titles, catalogue mappings, review queue |
| Bike variants collapsed | Overbroad name mapping | Preserved variant text and catalogue policy |
| High aggregate score, poor rare-model results | Dataset imbalance or sparse support | Per-family/variant errors and counts |
| Excellent random split, weak later predictions | Reposts, leakage, or market drift | Grouping and chronological holdout |
| Same listing's price never changes in saved data | Complete rows skipped on resume | Snapshot/history collection design |

Useful PowerShell checks:

```powershell
Get-Location
Get-ChildItem
python --version
python -m pip check
python scraper.py --self-test
```

## 22. Sources and handover notes

### Project evidence

- The supplied conversation states that the car scraper successfully scraped and cleaned data on the user's machine.
- The complete code in Section 5 is the previously supplied 12,850-byte `scraper.py`, preserved as the working baseline.
- The user's reported authorization includes a private review before publishing.
- The six bike families and their priority order are user-supplied; the national popularity order has not been independently measured here.
- Model-size targets, sampling quotas, acceptance criteria, and architecture choices are proposed engineering decisions, not externally established thresholds.

### Official technical references

- [pandas installation](https://pandas.pydata.org/docs/getting_started/install.html) — installation and environment guidance. Check actual dependency metadata for Python compatibility.
- [CatBoost categorical features](https://catboost.ai/docs/en/features/categorical-features) — support for categorical inputs.
- [CatBoost Python usage examples](https://catboost.ai/docs/en/concepts/python-usages-examples) — fitting, prediction, missing categorical placeholders, and model usage examples.
- [scikit-learn cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) — held-out evaluation and group/time-aware splitting concepts.

These sources support library behavior. They do not establish the proposed dataset quotas, bike popularity order, or any achieved prediction accuracy.

### Historical dataset option

The earlier conversation identified an [Open Data Pakistan used-car dataset](https://opendata.com.pk/dataset/pakistan-used-cars) as a possible historical starting point. Its earlier stated update date and reuse permissions have not been revalidated for this handbook. Treat it as an optional source to inspect, not current-market ground truth. Keep its source/date separate from newly collected data if it is reused.

### Status boundary

This file is a project handover and implementation guide. It contains the preserved car scraper and a standalone bike-name helper. It does not contain a completed live bike parser, trained predictors, or a deployed application. Those are explicitly planned stages, with completion criteria above.

### Verification performed for this handover

- Confirmed that the embedded scraper matches the recovered original file byte-for-byte.
- Parsed all seven Python code blocks for valid Python syntax; some are explicitly labelled patch sketches or interface placeholders.
- Ran both original offline car-parser self-tests successfully.
- Checked lac/crore conversion, zero mileage, ordered URL deduplication, incomplete-row retention, and raw/clean CSV save-and-load behavior.
- Ran all 11 bike-name normalization checks successfully, including variant retention and ambiguous/unmatched cases.
- Used Python 3.12 with pandas 3.0.6, requests 2.34.2, BeautifulSoup 4.15.0, and lxml 6.1.3 for the offline scraper checks. This is useful compatibility evidence for these operations, not proof of every dependency combination.
- Did not run a new live PakWheels crawl, train a predictor, or validate a live motorcycle parser during this handover.

Original scraper SHA-256: `9b166f637fe58ae564327f8a8de038348e80b9bc23582814ef6daf3cd23a0b52`.
