# Pakistan vehicle price predictor

The current stage is the data and modeling pilot. Reuse the working car collector, audit its evidence, then develop normalization, features, and model comparisons before a local demo.

- [Active pilot plan](docs/plans/DATA_MODELING_PILOT_PLAN.md)
- [Project journal](PROJECT_JOURNAL.md), updated after meaningful project work
- [Project handbook](docs/reference/PakWheels_Vehicle_Price_Predictor_Handbook.md)
- [Future production plan](docs/plans/PRODUCTION_IMPLEMENTATION_PLAN.md)
- [Framework research](docs/framework-research.md)
- [Coding practices reference](docs/reference/production_practices.md)

## Current structure

```text
pakwheels-price-predictor/
  scraper.py                    Working collector; output paths now organized
  requirements.txt              Existing collector dependencies
  PROJECT_JOURNAL.md            Development story and evidence
  pilot/
    audit.py                    Reusable offline CSV audit
    paths.py                    Audit defaults anchored to the project
  scripts/
    audit_data.py               Audit command entry point
  tests/
    test_audit.py               Data-integrity and review-preservation checks
  configs/
    pilot_scope.json            Draft; declares no supported models yet
  catalogues/                   Reviewed identity catalogues will go here
  docs/
    plans/                      Pilot and future production plans
    reference/                  Handbook and coding practices
    framework-research.md
  data/
    raw/
      baseline_2026-10-01/       Preserved original sample and collector
      current/                  Active collector CSVs
    processed/                  Future normalized training datasets
    debug_pages/                Private HTML/text diagnostics
    manifests/                  Future collection/dataset manifests
  reports/pilot/                Generated audit and manual review worksheet
  models/pilot/                 Future saved predictor artifacts
```

Private data, generated reports, diagnostics, model artifacts, and the local environment are excluded from Git. Project plans, journal, source, and directory documentation remain trackable. The baseline is a local preservation copy; maintain an independent private backup too.

## Use the existing Windows environment

Run commands from the project root. The existing `.venv` currently uses Python 3.13.7. Do not recreate it for this setup.

```powershell
Set-Location "D:\Coding Projects\pakwheels-price-predictor"
.\.venv\Scripts\python.exe --version
```

For a fresh checkout only, create an environment and install the current collector requirements:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The preserved baseline also records installed versions. No new dependency is needed for the offline audit or its tests.

## First step: offline audit

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_data
```

The default inputs are the preserved baseline CSVs. Outputs:

- [Stored-data audit](reports/pilot/initial_audit.md), regenerated when the command runs.
- [Identity review worksheet](reports/pilot/identity_review.csv), seeded with pending reviews and preserved on subsequent runs.

The audit checks schema, duplicate IDs/URLs, missing fields, numerical integrity, category counts, and consistency between the two exports. It does not fetch source pages or establish source correctness, training eligibility, or model reliability.

Review all ten original rows against available source evidence and record make/model/variant decisions in the worksheet. Record unavailable evidence explicitly. For a new batch, use a separate report directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_data --raw data/raw/current/pakwheels_raw.csv --clean data/raw/current/pakwheels_clean.csv --output-dir reports/pilot/current_batch
```

## Verify offline behavior

```powershell
.\.venv\Scripts\python.exe scraper.py --self-test
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The preserved original scraper is under `data/raw/baseline_2026-10-01/`. The current collector retains its parsing, delay, access-stop, and resume logic while using project-relative output directories.

## Collect a small authorized sample

Use collection only within the reported authorization. The next larger pilot follows the source audit. Current collector options:

```powershell
.\.venv\Scripts\python.exe scraper.py --pages 1 --ads 10 --delay 5 --contact "your-real-email@example.com"
```

For one advertisement, use `--url` with a current permitted PakWheels car listing URL. HTTP 401/403/429 stops the run. `--ads` still limits selected URLs, which may include previously saved complete listings; start-page and improved batch controls are future pilot work.

Collector output paths:

- `data/raw/current/pakwheels_raw.csv`: all parsed rows, including incomplete rows.
- `data/raw/current/pakwheels_clean.csv`: rows containing title, asking price, year, and mileage.
- `data/debug_pages/failed_<id>.html` and `.txt`: diagnostic evidence for incomplete listings.

The clean export is parser complete, not a reviewed training dataset. Preserve each batch before another run. Asking prices are not verified sale prices, and diagnostic HTML may include seller information. Keep the prototype and evidence private until the requested review.
