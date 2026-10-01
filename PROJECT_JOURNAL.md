# Project journal: Pakistan vehicle price predictor

Created: 1 October 2026. Last updated: 1 October 2026.

This is the living record of how the project develops: what we tried, what failed, what changed, the evidence behind decisions, and the results we obtained. Keep it updated after meaningful work sessions so it can support a later project report, portfolio case study, or technical handover.

The current implementation sequence is in [the data and modeling pilot plan](docs/plans/DATA_MODELING_PILOT_PLAN.md). [The handbook](docs/reference/PakWheels_Vehicle_Price_Predictor_Handbook.md) records earlier context. [The production plan](docs/plans/PRODUCTION_IMPLEMENTATION_PLAN.md) describes later options to reassess after the pilot.

## 1. How to maintain this record

- Append a dated story entry after a meaningful collection batch, investigation, preprocessing change, experiment, demo milestone, or architecture decision.
- Update the current status and unresolved-hurdle tables when work changes them. Preserve earlier dated snapshots and decisions rather than rewriting the past to match the latest result.
- Record the problem, evidence, attempted approaches, actual change, verification, outcome, and remaining limitations. Failed experiments are useful evidence too.
- Distinguish directly observed facts, user-reported results, historical handbook reports, hypotheses, and planned work.
- Give collection batches, datasets, experiments, and decisions stable IDs. Include the file/checksum, configuration, split ID, and code version needed to reproduce a result.
- Record unavailable values as `Not measured`, `Not available`, or `Not run`. Do not substitute zero for an unknown measurement.
- Explain the denominator behind a percentage. Parser completeness, manual extraction correctness, and model error measure different things.
- Record model metrics in PKR and by relevant subgroup. Do not describe regression results as a generic accuracy percentage.
- Reference private evidence by artifact or run ID. Keep seller contact details, credentials, and unredacted source HTML out of this journal.

Update this file as part of future project work; its creation does not establish an automatic background updater.

## 2. Current position

| Area | Status as of 1 October 2026 | Evidence or limitation |
|---|---|---|
| Goal | Estimate advertised asking prices in Pakistan, in PKR | Separate car and motorcycle predictors are intended |
| Car collector | Working script retained with organized output paths | Two offline parser checks and the export/resume storage check pass; no new live crawl performed |
| Initial car sample | Ten stored records, preserved with checksums | Baseline and active copies exist under `data/raw/` |
| Extraction correctness audit | Offline file checks completed; source verification pending | `reports/pilot/initial_audit.md` and a pending identity worksheet generated |
| Make/model/variant normalization | Planned | Current data retains titles rather than canonical identity columns |
| Motorcycle collector | Planned | Live motorcycle detail parsing has not been verified here |
| Feature selection | Candidate feature sets planned | No feature comparison has run |
| Algorithm selection | Pending experiments | Baseline, Ridge, Random Forest, and CatBoost are pilot candidates |
| Model training and evaluation | Not run in this session | No trained predictor or measured model score is claimed |
| Local demo | Planned | Follows the data/modeling pilot |
| Production framework and infrastructure | Deferred | FastAPI and managed infrastructure remain future recommendations |
| Publication | Private review required before public release | Authorization and review conditions are reported in the handbook |

Next work: verify the ten baseline rows against available source evidence and complete the identity review worksheet. Correct any demonstrated systematic extraction errors before collecting the next small batch. M0 preservation and offline checks are complete; manual verification remains open.

## 3. The project story so far

### J001: earlier parser failures and the revised collector

Recorded on 1 October 2026 from the handbook. The exact dates of the earlier changes are not available.

The earlier collector skipped advertisements when required regex matches were absent. It returned a generic failure instead of preserving the partial record. The handbook identifies a restrictive price expression and short search window as causes, including failure to handle prices such as `PKR 23.5 lacs`.

The revised collector added Pakistani price-unit conversion, broader scoped text searches and a price fallback, explicit missing-field names, raw incomplete rows, and saved HTML/text diagnostics. It also retained search-card discovery order instead of alphabetically sorting URLs, and saved results incrementally.

The current `scraper.py` contains these mechanisms. The handbook reports successful offline checks, and the user reports successful live collection. Those earlier tests were not rerun while preparing this journal.

Lesson: a collector should preserve enough evidence to explain a failed extraction. Quietly skipping an advertisement hides both parser errors and sampling bias.

### J002: the first available collected sample

Recorded on 1 October 2026. The CSV collection timestamps range from `2026-10-01T08:11:09.614635+00:00` to `2026-10-01T08:12:01.640269+00:00`.

Both current CSVs contain ten rows with ten unique listing IDs and ten unique URLs. Every stored row is marked complete under the scraper's title/price/year/mileage rule. The two files have the same SHA-256 checksum.

The sample includes electric, hybrid, petrol, and diesel cars, with several cities and complex trim names. Three electric-labelled records have no engine displacement. These observations exposed requirements for explicit non-applicability, careful identity normalization, and a limited first modeling scope.

This is evidence that data was saved. It is not a source-value audit or evidence of predictive quality. Total requests, failed fetches, and discarded historical records cannot be inferred from the saved rows.

### J003: considering production architecture early

Recorded on 1 October 2026.

The user requested a modular, clean, production-capable application plan with a reasoned framework choice. A production plan was created with module interfaces, practical SOLID principles, framework comparisons, reproducible model artifacts, deployment, security, monitoring, and recovery requirements.

FastAPI was recommended for explicit prediction contracts. Flask remained a viable alternative, and Django was considered attractive for substantial administration and account workflows. Supporting official-source research was saved in [the framework research note](docs/framework-research.md).

Outcome: the project has a future architecture reference. No web framework, database, cloud deployment, or production application was implemented as part of that planning work.

### J004: moving the execution plan back to data and modeling

Recorded on 1 October 2026.

The user clarified the intended sequence: reuse the working scraper, establish data/preprocessing/features, compare algorithms, build a small local demo, then train on larger data before moving into production work.

The earlier plan placed infrastructure decisions too early in the immediate workflow. A separate pilot plan was created, and the production plan was updated to defer its early implementation sequence.

The active approach is a feedback loop: audit a sample, validate extraction, normalize identities, compare feature sets and algorithms, build the demo, and use observed errors to guide larger collection. The small-data algorithm winner remains provisional until larger-data results support it.

Outcome: pilot milestones now control the next work. Production options remain documented for later reassessment.

### J005: establishing an evidence-based project journal

Recorded on 1 October 2026.

The user requested an ongoing account of the project's approach, hurdles, solutions, statistics, and results. This file was created with the available history, a verified starting CSV snapshot, decision and hurdle registers, and templates for future sessions.

Verification performed for this entry: counted CSV rows, unique listing IDs/URLs, stored parse statuses, missing engine fields, fuel/transmission/city distributions, and file hashes. No live scraping, source-value audit, model training, or application implementation was performed.

### J006: organizing the workspace and making the first audit runnable

Recorded on 1 October 2026.

The user requested the pilot's file structure and necessary initial files. The workspace now contained an initialized Git repository and a coding-practices reference. Its ignore patterns hid project documentation and included misspelled CSV filenames; the clean CSV was already present in the initial Git commit.

Plans moved into `docs/plans/`, and the handbook/practices reference into `docs/reference/`. The journal stayed at the root. Original CSVs, the original scraper, requirements, environment details, and checksums were preserved in `data/raw/baseline_2026-10-01/`. Active CSVs moved to `data/raw/current/`.

The collector's output paths and directory creation were adjusted to the new layout. Its parsing, pacing, access-stop, and resume rules were retained. A standard-library audit module and thin command were added, alongside a draft scope config and directory documentation. The audit generates a report and seeds pending identity reviews without overwriting an existing human worksheet.

Results: the offline audit confirms ten raw and ten parser-complete rows, ten unique IDs/URLs, three missing engine values, and matching complete/raw exports. It raises no flags from the implemented local checks. Source-value correctness, canonical identity, and training eligibility remain unverified.

Verification: six behavioral tests pass, covering zero mileage/EV missing values, invalid numbers/duplicates, malformed CSVs, manual-review preservation, inconsistent exports, and export/resume/diagnostic storage. Both existing offline parser self-tests pass. The existing environment is Python 3.13.7; no dependencies were installed.

Git ignore rules now exclude private outputs while allowing documentation and source to be tracked. The original CSV remains in earlier Git history; this setup does not rewrite that history. A local preservation copy still requires an independent backup.

Artifacts: baseline `manifest.json`, `environment.json`, and `requirements-lock.txt`; `reports/pilot/initial_audit.md`; `reports/pilot/identity_review.csv`; `pilot/audit.py`; `scripts/audit_data.py`; and tests. No new live collection, normalization decisions, model training, or web infrastructure was introduced.

Next step: manually review the ten rows and record available source evidence and make/model/variant decisions before M1 collection.

## 4. Hurdles and resolutions

Use an ID to connect each hurdle to its investigation, fix, and later verification entry. A known limitation is not necessarily a failure already encountered in a real run.

| ID | Hurdle | Evidence | Resolution or next action | Status |
|---|---|---|---|---|
| H001 | Earlier parser missed Pakistani abbreviated prices | Historical handbook account | Add lac/lakh/crore/million conversion and broader price extraction | Fix present; current offline self-tests pass |
| H002 | Generic skipped-row messages hid extraction causes | Historical handbook account | Preserve incomplete rows, missing fields, and debug evidence | Mechanism present; fresh verification pending |
| H003 | Alphabetical URL sorting could skew the selected sample | Historical handbook account and ordered-discovery implementation | Preserve source discovery order with ordered deduplication | Mechanism present; sample representativeness still needs review |
| H004 | Production infrastructure appeared too early in the execution plan | User clarification in this conversation | Introduce a separate data/modeling pilot and defer production work | Planning correction completed |
| H005 | Parser-complete data can still be wrong or unsuitable for training | Current completeness rule checks only four fields | Manually audit source values and add training eligibility rules | Local audit completed; source verification open |
| H006 | Titles contain model and variant details without normalized columns | Current CSV schema and sample titles | Reviewed catalogue, conservative resolution, ambiguity queue | Open |
| H007 | Missing engine displacement needs context for EVs | Three current electric-labelled rows lack `engine_cc` | Verify non-applicability; retain provenance instead of inventing zero | Identified; source verification pending |
| H008 | Repeated runs revisit early pages and count selected URLs rather than new rows | Current scraper control flow | Minimal start-page/batch controls and explicit run counters | Known limitation; change planned |
| H009 | Ten varied records cannot establish broad model reliability | Current sample size and lack of training results | Collect deeply within a limited, reviewed scope and evaluate held-out groups | Open |
| H010 | More data could multiply parser errors before they are discovered | Risk identified during planning | Audit early batches and resolve systematic errors before expanding | Prevention planned |
| H011 | Ignore patterns hid project records and misspelled output filenames | Workspace inspection during J006 | Replace them with explicit private-data patterns and retain trackable documentation | Fixed in working tree |

When a hurdle is solved, record the actual code/data change, date, verification, and story entry. Do not change `Open` to `Resolved` merely because a proposed fix has been written down.

## 5. Decision register

| ID | Decision | Reason | Status and revisit point |
|---|---|---|---|
| D001 | Predict advertised asking price in PKR | Source data contains listing prices, not verified transactions | Accepted scope |
| D002 | Start with a data/modeling pilot before production work | Data contracts and model evidence need to guide the application | Accepted execution sequence |
| D003 | Reuse the current scraper and change it incrementally | Existing collection logic works; the next changes should solve demonstrated needs | Accepted pilot approach |
| D004 | Use separate car and motorcycle predictors | Different identities, schemas, and price distributions | Planned implementation; evaluate each independently |
| D005 | Compare a median baseline, Ridge, Random Forest, and CatBoost | Test several useful modeling approaches with manageable experimental cost | Candidate list; no winner selected |
| D006 | Preserve variants, raw observations, and exclusion reasons | Avoid hidden identity loss and make preparation reproducible | Planned implementation |
| D007 | Keep preprocessing reusable between training and prediction | Prevent a demo from interpreting inputs differently from the trained model | Planned implementation |
| D008 | Build a local saved-predictor demo before large training | Verify the complete workflow at modest cost | Planned; CLI then a small local UI |
| D009 | Reassess framework and infrastructure after pilot results | Actual workflows, latency, memory, and durability needs remain unknown | Deferred; production handover milestone |

Add new decisions rather than silently replacing old ones. If a decision changes, mark it superseded and link its replacement entry.

## 6. Dataset snapshot S001

Observed on 1 October 2026 from the current files. This is a dated snapshot; future data updates should receive a new snapshot ID.

| Statistic | Value | Interpretation |
|---|---:|---|
| Raw CSV rows | 10 | Stored records, not total requests |
| Clean CSV rows | 10 | Parser-complete records |
| Unique listing IDs | 10 | Exact IDs in the stored sample |
| Unique source URLs | 10 | Exact URLs in the stored sample |
| Duplicate listing IDs within each file | 0 | Does not rule out reposts under different IDs |
| Stored incomplete rows | 0 | Does not establish that no request or historical extraction failed |
| Stored parser completeness | 100% | Ten complete rows divided by ten raw rows |
| Missing engine displacement | 3 of 10 | All three are labelled Electric; source correctness not yet audited |
| Represented listing cities | 5 | City labels in the CSV |
| Reviewed source-correct rows | Not measured | Manual audit pending |
| Canonically resolved identities | Not measured | Normalization pending |
| Unique vehicle/repost groups | Not measured | Grouping pending |
| Training-eligible records | Not measured | Model-specific quality rules pending |

### Stored category counts

| Dimension | Counts |
|---|---|
| Fuel | Petrol 5; Electric 3; Hybrid 1; Diesel 1 |
| Transmission | Automatic 9; Manual 1 |
| Listing city | Lahore 4; Karachi 3; Islamabad 1; Rawalpindi 1; Peshawar 1 |

These describe the ten stored observations. They are not estimates of national vehicle ownership, marketplace popularity, or deployment traffic.

### File fingerprints

SHA-256 values observed locally:

| Artifact | Checksum |
|---|---|
| `pakwheels_raw.csv` | `1016b4169ffeeb21837a424317522eea1c8679a32c3d9b42c07c929b67c03aed` |
| `pakwheels_clean.csv` | `1016b4169ffeeb21837a424317522eea1c8679a32c3d9b42c07c929b67c03aed` |
| Current `scraper.py` | `8c4246c10e7d01645e6a2af04112edf901eb7e2ca77ee2b1e79a2de14b72d2e3` |

The handbook records a different checksum for its recovered original scraper. Byte identity between that historical artifact and the current file has not been established. A checksum difference alone does not identify a behavioral change.

## 7. Collection and experiment results

### Collection ledger

| Batch ID | Date | Scope | Requests | Stored rows | Eligible groups | Evidence |
|---|---|---|---|---:|---|---|
| Legacy sample S001 | 1 October 2026 | Car listings in current CSVs | Not available | 10 | Not measured | User-reported collection; current files inspected |

For future batches add discovery/detail request counts, duplicates, access stops, ordinary failures, incomplete rows, exclusion counts, review sample size, actual discrepancies, elapsed time, and dataset checksum. Distinguish newly added rows from cumulative totals.

### Model experiment ledger

No model experiment results are available yet.

When experiments run, record:

| Experiment ID | Dataset/split | Features | Model and configuration | Validation MAE PKR | Final test MAE PKR | Result |
|---|---|---|---|---|---|---|

Include fold variability, median error, subgroup counts/errors, training time, and artifact references in the associated story entry. Label exploratory, selected, rejected, and superseded experiments explicitly. A final-test metric is `Not run` until the frozen candidate is evaluated.

### Demonstrated milestones

- Working collection logic and ten stored records are available.
- A production architecture reference and an active pilot plan have been written.
- The workspace is organized, the initial sample is preserved, and offline audit/review files are generated.
- Six behavioral tests and both existing parser self-tests pass in the current environment.
- A local prediction demo, trained model, measured regression result, and deployed application are pending.

## 8. Reusable story-entry template

Append completed entries to Section 3 in chronological order. Use only the fields relevant to the work; collection or training details can live in linked reports.

```markdown
### J007: <specific event or milestone>

Date: YYYY-MM-DD. Stage: <pilot milestone>. Status: <investigating/completed/blocked>.

Goal: <what we intended to establish or improve>.

Starting point: <dataset ID, code version, and known behavior>.

Problem and evidence: <observed failure, discrepancy, or uncertainty; link evidence>.

Approaches tried: <what we attempted, why, and what each attempt showed>.

Change or decision: <actual code/data/configuration change and rationale>.

Verification: <checks performed, manual sample, split policy, and reproducible command>.

Results: <before/after numbers with denominators and units; unknowns explicitly marked>.

Limitations: <what remains uncertain, unsupported, or unverified>.

Lesson: <what this changes about the next step>.

Artifacts: <batch/dataset/experiment IDs, reports, model path, hashes, commit if available>.

Next step: <concrete follow-up and completion condition>.
```

For a solved bug, include how it was reproduced and which verification would catch a recurrence. For a rejected model, preserve its configuration and the evidence that led to rejection. For a planning correction, record the changed priority without presenting it as an implementation result.

## 9. Statistics to add as the project grows

| Area | Useful measurements | How to interpret them |
|---|---|---|
| Collection | Requests, response outcomes, elapsed time, new IDs, parser completeness, failed URLs | Report per batch and cumulatively with clear denominators |
| Manual audit | Reviewed rows/fields, incorrect extractions, error types, affected strata | A review sample is evidence, not a guarantee about every row |
| Coverage | Family/variant/year/city/mileage distributions, missingness | Identify gaps and bias rather than celebrating raw volume |
| Normalization | Matched, ambiguous, unmatched, reviewed variants, catalogue version | Measure how much usable identity evidence exists |
| Quality filtering | Retained/excluded/flagged records by reason | Explain where training data came from |
| Evaluation | Group counts, split membership, MAE, median error, percentage error, subgroup counts | Keep validation and untouched test results separate |
| Model selection | Feature ablations, baseline improvement, fold variation, training/inference time | Establish whether complexity adds useful evidence |
| Scaling | Errors versus independent training size, newly covered identities, data age | Determine whether more data helps |
| Demo | Supported inputs, save/load equivalence, refused cases, user feedback | Show a usable workflow and its actual limits |
| Later production | Release IDs, observed latency/error rates, incidents, recovery time | Record measured operation after deployment exists |

Use dated snapshots for changing statistics. Attach report or artifact references so a later summary can trace every headline number to its evidence.
