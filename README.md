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
- [First pilot quality review and preparation rules](docs/pilot-data-review.md)
- [Shared features and fixed evaluation splits](docs/pilot-evaluation-contract.md)

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
    persistence.py              Bounded retries for Windows file replacement
  pilot/
    audit.py                    Reusable offline CSV audit
    paths.py                    Audit defaults anchored to the project
    identity.py                 Catalogue-based family and variant resolution
    evidence.py                 Cached source comparisons and repair evidence
    quality.py                  Candidate rules and possible-repost groups
    profile.py                  Coverage and missingness reports
    features.py                 Shared unfitted training/prediction inputs
    splits.py                   Deterministic family/group assignments
    evaluate.py                 Frozen population and development-data loader
  scripts/
    audit_data.py               Audit command entry point
    validate_collection.py      Reparse cached sample or fetch missing evidence
    prepare_dataset.py          Offline versioned preparation command
    prepare_evaluation.py       Freeze feature contract and evaluation splits
  tests/
    test_audit.py               Data-integrity and review-preservation checks
    test_collection_fields.py   New-field meaning and contamination checks
  configs/
    pilot_scope.json            Four candidate families; no predictor support yet
    collection_schema.json      Version 2 field decision contract
    collection_pilot.json       Four family quotas plus general discovery
    evaluation_pilot.json       Fixed seed, reserved test, three validation folds
  catalogues/cars.json           Four families and observed variant labels
  docs/
    plans/                      Pilot and future production plans
    reference/                  Handbook and coding practices
    framework-research.md
  data/
    raw/
      baseline_2026-10-01/       Preserved original sample and collector
      current/                  Active collector CSVs
      field_validation_2026-10-01/  Separate enriched ten-listing sample
      pilot_batch_001/           User-collected 200-record field pilot
    processed/pilot_batch_001_v2/  Final normalized/candidate datasets
    processed/pilot_batch_001_eval_v1/  Frozen contracts and split membership
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

The user has confirmed the ten original records are accurate. The extended schema was checked on those ten listing pages in a separate validation batch. The user then collected 200 records in `pilot_batch_001`, reaching all 180 assigned complete matches. Its offline quality review and initial preparation are complete. For a new batch, use a separate report directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_data --raw data/raw/current/pakwheels_raw.csv --clean data/raw/current/pakwheels_clean.csv --output-dir reports/pilot/current_batch
```

## Current prepared dataset

Version `pilot_batch_001_v2` contains 200 normalized observations, 137 candidates from four families in model years 2010–2026, and 72 candidates whose cached visible asking price agrees with their URL-matched structured offer. Sixty-five other candidates remain pending price verification. Source agreement does not validate a seller's claims or a sale price.

Cached evidence identified a recommended-car price contaminating one Civic's extraction and an unsupported PHEV fuel label. Both parser issues were fixed; evidenced repairs are recorded in derived files, with raw data preserved. See [the review](docs/pilot-data-review.md) and [generated quality report](reports/pilot/pilot_batch_001/data_quality.md).

Preparation reads saved files only. The default output already exists, so use a new directory to reproduce it:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_dataset --output-dir data/processed/pilot_batch_001_v3 --report-dir reports/pilot/pilot_batch_001_v3
```

The observed-label catalogue preserves trims. Registration semantics remain unknown and registration features are deferred. Shared F0–F2 input rules and fixed splits are implemented. No model, fitted preprocessing, or prediction support has been finalized.

## Fixed exploratory evaluation

The 72 source-checked records now have saved membership: 57 development records and 15 reserved demo-test records. Three validation folds each contain 19 development records; each run trains on the other 38. Every family appears in every fold. F0–F2 share these assignments, and possible repost groups stay together.

The loader verifies dataset/artifact hashes and defaults to development data. The reserved test requires an explicit request and has no model outcomes yet. See [the evaluation contract](docs/pilot-evaluation-contract.md) and [generated split report](data/processed/pilot_batch_001_eval_v1/split_report.md).

To reproduce offline into a new directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_evaluation --output-dir data/processed/pilot_batch_001_eval_v2
```

Next is exploratory M3 comparison using training-fold-only preprocessing. Three or four test records per family cannot establish a reliable four-family demo.

## Verify offline behavior

```powershell
.\.venv\Scripts\python.exe scraper.py --self-test
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The preserved original scraper is under `data/raw/baseline_2026-10-01/`. The current collector keeps core parsing, pacing, and access-stop behavior, and adds optional attributes with explicit provenance. Forty-five behavioral tests pass with HTTP requests blocked. Both existing parser self-tests passed during the previous quality-review step. No live collector was launched.

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

This targets 40 Corolla, 40 City, 40 Civic, 40 Alto, and 20 general-discovery listings. Maximum budgets are 250 detail attempts and 25 search pages. This batch has already met its quotas; rerunning it without refresh does not expand the modeling dataset. A deeper scoped collection needs a new configuration and batch directory.

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
