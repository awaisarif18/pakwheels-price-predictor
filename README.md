# PakWheels car-price research collector

The [project journal](PROJECT_JOURNAL.md) records development history, hurdles, decisions, verified statistics, and experiment results. Update it after meaningful project work. The [data and modeling pilot plan](DATA_MODELING_PILOT_PLAN.md) defines the current implementation sequence.

Use only within the scope of access authorized by PakWheels. The program is intentionally sequential and stops at HTTP 401/403/429 rather than circumventing restrictions. Please keep output private until the requested review.

## Windows PowerShell setup

```powershell
cd "D:\Coding Projects\pakwheels-price-predictor"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Confirm the parser works without internet access

```powershell
python scraper.py --self-test
```

## Test just one advertisement

```powershell
python scraper.py --url "https://www.pakwheels.com/used-cars/honda-city-2022-for-sale-in-islamabad-12001735" --contact "your-real-email@example.com"
```

## Small, approved sample of search results

```powershell
python scraper.py --pages 1 --ads 10 --delay 5 --contact "your-real-email@example.com"
```

## Outputs

- `pakwheels_raw.csv`: every parsed listing, including incomplete rows and `missing_fields`.
- `pakwheels_clean.csv`: rows that have a title, asking price, year and mileage.
- `debug_pages/failed_<id>.html`: returned HTML for unsuccessful extraction.
- `debug_pages/failed_<id>.txt`: which fields were missing and the first part of visible listing text.

The CSV represents *advertised asking prices*, not verified sale transactions. Check a sample manually before training. Debug HTML may include sellers' personal information: redact it before sharing publicly.

If extraction fails for all ads, look in `debug_pages` first. The site can deliver different markup to a script than to a browser. No live scraping has been executed to validate selectors from this environment.
