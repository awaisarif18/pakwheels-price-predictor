# Pakistan vehicle price predictor

The current stage is the data and modeling pilot. Reuse the working car collector, audit its evidence, then develop normalization, features, and model comparisons before a local demo.

- [Active pilot plan](docs/plans/DATA_MODELING_PILOT_PLAN.md)
- [Project journal](PROJECT_JOURNAL.md), updated after meaningful project work
- [Project handbook](docs/reference/PakWheels_Vehicle_Price_Predictor_Handbook.md)
- [Future production plan](docs/plans/PRODUCTION_IMPLEMENTATION_PLAN.md)
- [Framework research](docs/framework-research.md)
- [Coding practices reference](docs/reference/production_practices.md)
- [Collection fields and validation findings](docs/collection-field-mapping.md)
- [Run the field collection pilot](docs/collection-pilot-run.md)

## Current structure

```text
pakwheels-price-predictor/
  scraper.py                    Collector with batch, refresh, and page controls
  requirements.txt              Existing collector dependencies
  PROJECT_JOURNAL.md            Development story and evidence
  collector/
    fields.py                   Optional attributes, identity, and provenance
    sampling.py                 Validated search configuration and family matching
    runner.py                   Bounded collection, resume, and round-robin groups
    run_log.py                  Request accounting and batch summary
  pilot/
    audit.py                    Reusable offline CSV audit
    paths.py                    Audit defaults anchored to the project
  scripts/
    audit_data.py               Audit command entry point
    validate_collection.py      Reparse cached sample or fetch missing evidence
  tests/
    test_audit.py               Data-integrity and review-preservation checks
    test_collection_fields.py   New-field meaning and contamination checks
  configs/
    pilot_scope.json            Draft; declares no supported models yet
    collection_schema.json      Version 2 field decision contract
    collection_pilot.json       Four family quotas plus general discovery
  catalogues/                   Reviewed identity catalogues will go here
  docs/
    plans/                      Pilot and future production plans
    reference/                  Handbook and coding practices
    framework-research.md
  data/
    raw/
      baseline_2026-10-01/       Preserved original sample and collector
      current/                  Active collector CSVs
      field_validation_2026-10-01/  Separate enriched ten-listing sample
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

The user has confirmed the ten original records are accurate. The extended schema has been checked on those ten listing pages in a separate validation batch. Make/model/variant are source-normalized, with canonical catalogue review pending. The varied collection controls are ready; the next batch awaits user execution. For a new batch, use a separate report directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_data --raw data/raw/current/pakwheels_raw.csv --clean data/raw/current/pakwheels_clean.csv --output-dir reports/pilot/current_batch
```

## Verify offline behavior

```powershell
.\.venv\Scripts\python.exe scraper.py --self-test
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The preserved original scraper is under `data/raw/baseline_2026-10-01/`. The current collector keeps core parsing, pacing, and access-stop behavior, and adds optional attributes with explicit provenance. Twenty-five behavioral tests pass. The two existing parser self-tests passed during the previous step; they were not rerun as a scraper command during this user-operated handoff.

Reproduce new-field extraction from cached pages without network access:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_collection
```

## User-operated collection pilot

Live collection is run by the user. The agent prepares and checks code offline, supplies a PowerShell command, and waits for completion before inspecting outputs. See [the pilot run guide](docs/collection-pilot-run.md) for quotas, progress files, and resume behavior.

```powershell
Set-Location "D:\Coding Projects\pakwheels-price-predictor"
$researchContact = Read-Host "Enter your collector contact email"
.\.venv\Scripts\python.exe scraper.py --sampling-plan configs/collection_pilot.json --output-dir data/raw/pilot_batch_001 --delay 5 --contact $researchContact
```

This targets 40 Corolla, 40 City, 40 Civic, 40 Alto, and 20 general-discovery listings. Maximum budgets are 250 detail attempts and 25 search pages. Actual results can fall short and will be reported.

## Small manual sample

Use collection within the reported authorization. Write each new batch to its own directory:

```powershell
.\.venv\Scripts\python.exe scraper.py --pages 1 --ads 10 --start-page 1 --delay 5 --output-dir data/raw/manual_sample_001 --contact "your-real-email@example.com"
```

For one advertisement, use `--url` with a current permitted PakWheels car listing URL. HTTP 401/403/429 stops the run. `--refresh` re-fetches selected saved complete rows; otherwise they are skipped. `--ads` now limits actual detail attempts, including failed requests. Saved-row skips and duplicate IDs do not consume it. Both manual and planned runs write a manifest, per-run log, and summary.

New fields include make/model/variant, assembly, body type, optional registration year, and listing date with its meaning. All ten sample dates were labeled `Last Updated`; nine explicit registration years were found, with unknown registration meaning. Registration location, colour, and subjective condition claims are excluded. See [the source mapping](docs/collection-field-mapping.md) for definitions and limits.

Default collector output paths, used when `--output-dir` is omitted:

- `data/raw/current/pakwheels_raw.csv`: all parsed rows, including incomplete rows.
- `data/raw/current/pakwheels_clean.csv`: rows containing title, asking price, year, and mileage.
- `data/raw/current/evidence/`: representative detail HTML and incomplete-row previews.
- `data/raw/current/diagnostics/`: search pages with no recognized listing links.
- `data/raw/current/manifest.json`, `runs/`, and `collection_summary.md`: collection accounting.

The clean export is parser complete, not a reviewed training dataset. Preserve each batch before another run. Asking prices are not verified sale prices, and diagnostic HTML may include seller information. Keep the prototype and evidence private until the requested review.
