# First field pilot: quality review and preparation contract

Date: 2 October 2026. Active plan: [data and modeling pilot](plans/DATA_MODELING_PILOT_PLAN.md), M1 quality review and initial M2 preparation.

## What is complete

The user collected `pilot_batch_001`. Offline checks found 200 unique listing IDs, 199 parser-complete records, and consistent raw/clean exports. All 180 assigned collection matches were obtained. Actual family membership differs from assigned quotas because some search results contained other families.

| Family | Observed records | Candidates, years 2010–2026 | Candidates with cached price agreement |
|---|---:|---:|---:|
| Toyota Corolla | 41 | 37 | 18 |
| Honda City | 41 | 36 | 16 |
| Honda Civic | 45 | 30 | 18 |
| Suzuki Alto | 43 | 34 | 20 |
| Total | 170 | 137 | 72 |

The initial candidate scope is these four families and model years 2010–2026. This limits older, sparsely represented generations while retaining the main collection targets. It is a provisional modeling choice, not evidence that every year or trim in that interval can be predicted reliably. All observed cities remain available for evaluation. `supported_models` remains empty.

The prepared dataset is [pilot_batch_001_v2](../data/processed/pilot_batch_001_v2/manifest.json). The generated [quality report](../reports/pilot/pilot_batch_001/data_quality.md) includes coverage, missingness, corrections, and input fingerprints.

## Source review and parser corrections

There were 108 cached listing pages. Every referenced HTML checksum was validated. URL-matched structured products supplied 642 comparisons of price, model year, mileage, fuel, transmission, and engine displacement: 640 agreed with stored values and two differed. One cached page had no matching product because its asking price was unspecified.

| Listing ID | Finding | Resolution |
|---|---|---|
| 11874852 | A Civic's stored PKR 3,095,000 came from a recommended car. Its own visible price and URL-matched offer both stated PKR 4,850,000. | Corrected the derived price; changed the parser to prefer the current listing's main price box and remove recommendation cards from fallback text. |
| 12033889 | A Haval H6's fuel was empty despite an explicit PHEV source value. | Added PHEV parsing and corrected the derived fuel from cached evidence. |
| 12075118 | Prado says Call for price. | Retained the missing target and excluded it from modeling. Never substitute a recommendation's price. |

An uncached Chery PHEV listing still has missing fuel. Its title alone was not used to invent a repair. Uncached records remain unverified rather than automatically wrong.

Price agreement requires the listing's visible main price to agree with its URL-matched structured offer. This verifies extraction against a saved snapshot. It does not validate seller claims, establish a transaction price, or certify all 200 records. The evidence sample follows the collector's retention policy and is not a random accuracy sample.

Raw CSVs and cached HTML were preserved. Repairs exist only in derived files, with `source_updates` and evidence paths/checksums. The price-selection, Call for price, and PHEV regressions failed before the parser fix and passed afterward.

## Deterministic preparation rules

Responsibilities are separated into identity resolution (`pilot/identity.py`), cached evidence review (`pilot/evidence.py`), eligibility and grouping (`pilot/quality.py`), and reporting (`pilot/profile.py`). `scripts/prepare_dataset.py` coordinates these functions. No application framework or model dependency was added.

1. Check input schema, exact duplicate IDs/URLs, numerical integrity, and agreement between complete raw rows and the clean export.
2. Resolve four family names and observed variant labels using [the catalogue](../catalogues/cars.json). Normalize case and whitespace; preserve trim distinctions. Unknown variants remain unresolved, and an unspecified variant never becomes base trim.
3. Normalize category placeholders such as N/A to missing. Preserve meaningful metadata such as `registration_year_meaning=unknown` and zero mileage. Convert integral numerical values without clipping prices or mileage to arbitrary thresholds.
4. Require a positive asking price, valid model year, nonnegative mileage, an in-scope family/year, and resolved identity for candidates. An unspecified variant is explicitly flagged but retained for feature comparisons. Optional missing values remain visible.
5. Apply repairs only when supported by cached evidence. Exclude unresolved source disagreements from candidates.
6. Group exact specification matches conservatively as possible reposts, excluding price from the grouping key. Keep every observation. No multi-record groups were found in this batch; different IDs/specifications do not prove different vehicles.
7. Export all normalized observations, candidate rows, and a separate candidate subset with cached price agreement. Record exclusions, quality notes, checksums, and code/configuration versions.

| Output in `data/processed/pilot_batch_001_v2/` | Rows | Purpose |
|---|---:|---|
| `normalized_all.csv` | 200 | Recoverable normalized observations, including excluded records and reasons |
| `modeling_candidates.csv` | 137 | In-scope candidates; 65 still lack cached price verification |
| `source_checked_candidates.csv` | 72 | Conservative initial population for exploratory experiments |
| `manifest.json` | — | Input/output/code hashes, scope, corrections, and training status |

Sixty-three rows are excluded overall. Reasons can overlap: 40 outside the year interval, 30 outside the four families, and one missing price. Within the four families, 33 older records account for the reduction from 170 to 137. They remain in the normalized export.

The intermediate `pilot_batch_001_v1` was superseded during development: a regression test caught generic placeholder normalization erasing the meaningful registration status `unknown`. Version 2 preserves that metadata. Use version 2 for subsequent work.

## Feature decisions and remaining limits

- F0: make, model, year, mileage, listing city.
- F1: F0 plus preserved variant.
- F2: F1 plus fuel, transmission, engine displacement, assembly, body type.
- Registration year remains an optional stored fact. Only 40/137 candidates contain it, with unknown meaning; defer F3 and do not derive registration gaps or physical usage.
- All observed listing dates mean Last Updated. Use these and collection timestamps as freshness metadata; they do not establish original publication dates.
- IDs, URLs, asking-price-derived values, provenance, eligibility flags, and grouping metadata are not prediction features.

After placeholder normalization and evidenced corrections, five of 200 observations lack body type, rather than the one suggested by nonempty raw values. The 137 candidates have one missing body type and one unspecified variant. Their other F0–F2 fields are populated. All 72 source-checked candidates have populated F0–F2 fields, but completeness is not proof of predictive usefulness.

Coverage remains thin: 42 candidate family/variant combinations, of which 31 have three or fewer records; 17 cities, of which 12 have three or fewer records. Lahore, Karachi, Islamabad, and Rawalpindi account for 115/137 candidates. Collection ordering makes this a convenience sample, not an estimate of Pakistan's market distribution.

No imputer, encoder, scaler, rare-category grouping, or target transform has been fitted. Those decisions belong inside training folds in M3. No fixed split, trained model, final-test result, or supported demo input contract exists yet.

## Reproduce preparation offline

The existing version 2 output is preserved; the command refuses an existing output directory. To reproduce into a new version and separate report directory:

```powershell
Set-Location "D:\Coding Projects\pakwheels-price-predictor"
.\.venv\Scripts\python.exe -m scripts.prepare_dataset --batch-dir data/raw/pilot_batch_001 --output-dir data/processed/pilot_batch_001_v3 --report-dir reports/pilot/pilot_batch_001_v3
```

This reads saved files only. No scraping or new dependency is needed. Verification completed: 36 behavioral tests and both original parser self-tests passed with HTTP requests blocked. Raw-file fingerprints still match the preparation manifest.

## Next stage

J014 update, 2 October 2026: shared F0–F2 preparation and fixed splits are now implemented. The [evaluation contract](pilot-evaluation-contract.md) records 57 development rows, three 19-row validation folds, and 15 reserved demo-test rows. No model comparison or fitted preprocessing has run. The following describes the sequence established by this review.

Continue M2 by defining fixed group-aware development/evaluation splits and shared feature construction, then begin an explicitly exploratory M3 benchmark on the 72 source-checked candidates. That can test the workflow and reveal errors before a larger run. With only 16–20 checked records per family, it cannot establish a reliable four-family demo.

Use the measured coverage gaps to prepare a deeper scoped modeling collection toward the plan's roughly 500–1,500 usable records. Record source-price checks, variant/year coverage, and batch identity before finalizing demo support. Each live run is handed to the user as an exact PowerShell command; the agent waits for completion. Algorithm choice and fitted preprocessing remain experimental decisions, and production work follows the predictor/demo milestones.
