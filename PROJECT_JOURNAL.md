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
| Car collector | Optional attributes, family sampling, bounded requests, and batch accounting implemented | Twenty-five offline behavioral tests pass; previous ten-page live validation remains evidence for field extraction |
| Initial car sample | Ten stored records, preserved with checksums | Baseline and active copies exist under `data/raw/` |
| Extraction correctness audit | Original ten records confirmed by user; added fields checked on ten source pages in J009 | Canonical identity and broader batch quality review remain pending |
| Make/model/variant normalization | Source-normalized identity extracted on ten pages | Canonical catalogue review remains pending; unresolved identities are explicit |
| Motorcycle collector | Planned | Live motorcycle detail parsing has not been verified here |
| Feature selection | Candidate feature sets planned | No feature comparison has run |
| Algorithm selection | Pending experiments | Baseline, Ridge, Random Forest, and CatBoost are pilot candidates |
| Model training and evaluation | Not run in this session | No trained predictor or measured model score is claimed |
| Local demo | Planned | Follows the data/modeling pilot |
| Production framework and infrastructure | Deferred | FastAPI and managed infrastructure remain future recommendations |
| Publication | Private review required before public release | Authorization and review conditions are reported in the handbook |

Next work: the user runs the prepared [collection pilot command](docs/collection-pilot-run.md), then reports completion. The agent will inspect saved results offline, measure missingness by family/year/city, and review identity and assembly quality. Live collection is reserved for the user in [AGENTS.md](AGENTS.md). No new collection batch has been executed in J010.

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

### J007: accepting the sample confirmation and examining missing attributes

Recorded on 1 October 2026.

The user confirmed that the ten collected records contain accurate data and requested a reasoned explanation of current and additional attributes. This confirmation is accepted as user-reported source verification. Identity normalization and training suitability are separate questions.

The existing CSV has 13 fields. Vehicle details include title, year, mileage, fuel, transmission, engine displacement, and listing city. Asking price is the target; the remaining columns record provenance and parser diagnostics. Make/model/variant are present in title wording but have not been separated into canonical columns.

The handbook proposes additional assembly, registration location, and body-type attributes. A read-only web inspection of the sample Corolla listing also showed colour, a listing date, and inspection information. Availability on one listing does not establish coverage across the marketplace or predictive improvement. Attribute priorities and their actual extraction semantics remain under discussion.

Next work: settle which attributes to retain during the collection pilot, normalize vehicle identity, and compare feature sets on consistent evaluation groups. Additional-field extraction checks remain necessary as fields are introduced; repeating the baseline accuracy audit is unnecessary.

### J008: consolidating the next collection schema

Recorded on 1 October 2026.

The user accepted assembly and body type, chose to retain listing date and registration year, and excluded registration location, colour, and subjective seller condition claims. Listing city remains part of the existing data.

These choices are recorded in `configs/collection_schema.json` and the active pilot plan. Registration year is an optional collected attribute whose incremental modeling value must be evaluated; it does not replace model year or establish physical usage. Listing date is initially metadata for freshness and evaluation, with posted/updated/unknown semantics preserved separately from collection time.

The next implementation begins with representative source mapping because registration year may be absent or ambiguous and a displayed date may describe an update. New optional attributes must not invalidate otherwise complete rows. Identity normalization remains necessary. No new field extraction or live batch was run while recording this decision.

### J009: implementing and validating the agreed collection fields

Date: 1 October 2026. Stage: M0-to-M1 collection preparation. Status: completed for the ten-page validation sample.

Goal: implement assembly, body type, registration year, listing date, and make/model/variant extraction without changing the original core parser or starting application infrastructure.

Source investigation: fetched the ten original listing URLs sequentially, with five seconds between requests. Four initial inspection requests established the markup; the validation command fetched six remaining pages and reused those four cached files. All requests succeeded. This is new-field validation, not a repeated requirement to establish the user-confirmed baseline accuracy.

Problems found: pages embed JSON-LD for recommendations as well as the current car. The visible date is labeled `Last Updated`. Registration year is not in the labeled specification table and can appear in explicit factual seller comments. The two Audi e-tron listings report different assembly values, requiring later source-quality review.

Changes: added `collector/fields.py` as an offline extraction module. Structured identity must match the current listing URL; conflicting products remain unresolved. Explicit table labels supply assembly/body type/date. Registration extraction accepts factual statements, preserves unknown jurisdiction meaning, and never substitutes model year or ownership transfer. Added provenance, status, and schema-version columns. Variant names retain source wording and are pending catalogue review.

Collection controls: `--output-dir` isolates batches, `--refresh` deliberately re-fetches selected saved rows, and `--start-page` lets collection progress beyond the first page. Old-schema rows can be resumed/exported without fabricating new attributes. The preserved baseline is blocked as a CLI output directory. The general collector still caps selected URLs with `--ads`; complete general batch accounting and family sampling remain pending.

Results: separate batch `field_validation_2026-10-01` contains 10/10 parser-complete rows. Make, model, variant, assembly, body type, and listing date each have 10/10 non-null values. Registration year has 9/10, all with unknown registration meaning. All ten date labels mean updated. Fortuner model year 2022 has stated registration year 2023; Raize model year 2021 has stated registration year 2025. Neither difference establishes usage or condition.

Verification: inspected table labels and explicit registration evidence across all ten cached pages. Fifteen behavioral tests and the two original parser self-tests pass. The enriched raw/clean exports pass the existing integrity audit. Both preserved baseline CSVs and both original active CSVs retain their original checksum; the original review worksheet was not rewritten. The validation batch has cached HTML hashes and a request/evidence manifest. Reproduction is offline via `python -m scripts.validate_collection`.

Limitations: ten listings do not establish marketplace-wide availability or factual correctness. The same ten IDs are not additional independent training vehicles. Initial inspection downloads predate the manifest and use cache-file timestamps. Standalone registration parsing deliberately leaves unsupported free-text formats unresolved. No model training or feature comparison has run.

Lesson: verify source labels before assigning meaning. An update date cannot become a posting date through normalization, and exact extraction does not certify seller-entered assembly information.

Artifacts: [field mapping and results](docs/collection-field-mapping.md), [schema contract](configs/collection_schema.json), private batch under `data/raw/field_validation_2026-10-01/`, private audit under `reports/pilot/field_validation_2026-10-01/`.

Next step: implement controlled family sampling and general collection summaries, then collect 100-300 varied records to measure missingness, resolve identities, and choose the first modeling scope.

### J010: preparing controlled sampling and a user-operated collection handoff

Date: 1 October 2026. Stage: M1 preparation. Status: code preparation completed; live pilot awaiting user execution.

User instruction: prepare the next step but never launch live scraping. When a run is needed, supply a PowerShell command, stop, and wait for the user to finish and ask to continue. Recorded this persistent workflow in `AGENTS.md`.

Starting point: schema version 2 and ten-page field validation were complete. The scraper still relied on general search order, counted selected saved URLs against `--ads`, and lacked general run accounting.

Source evidence: inspected cached HTML only. Those pages link to Corolla, City, Civic, and Alto search routes. Their live result pages and current availability remain unverified in this step.

Implementation: added validated sampling configuration with four 40-row family targets and 20 general-discovery rows. Targets count complete extracted family matches, not every request or title. Round-robin collection alternates groups, with at most 250 detail attempts and 25 search pages per run. Request failures consume detail budgets; duplicate IDs and saved-row skips do not. Unexpected-family and incomplete observations remain in raw storage.

Architecture: `collector/sampling.py` validates search definitions and family matching; `collector/runner.py` handles sequencing, limits, and resume; `collector/run_log.py` records requests, outcomes, and summaries. `scraper.py` retains fetching, parsing, storage helpers, and the CLI. No application framework or new dependency was introduced.

Durability and evidence: parsed rows are saved incrementally. CSV, manifest, and log writes use temporary-file replacement. Ctrl+C and access restrictions preserve completed work and record a stop status. Batch plan mismatches are rejected before collection. Representative HTML is retained for the first 50 complete observations per run, all flagged cases, and an expected 10% hash sample afterward. The batch manifest distinguishes cumulative rows from latest-run requests and selections.

Verification: 25 behavioral tests passed with `requests.sessions.Session.request` blocked. New checks exercise alternating groups, quotas, incomplete and unexpected-family retention, duplicate IDs, skipped saved rows, ordinary request failures, access stops, operator interruption, empty searches, completed-plan resume, changed-plan rejection, and invalid configuration. All test outputs were temporary. No live request, scraper command, or new collection batch was launched by the agent in this step.

Results: ready-to-run configuration targets 180 complete matches across five groups; actual rows, request outcomes, field availability, and family coverage are `Not run`. The 180 target is not a measured result or prediction-support claim. Existing baseline and validation artifacts remain unchanged.

Limitations: family search behavior still needs the user-operated run. Marketplace ordering and featured ads can bias selection; cities, years, and variants have no balance guarantee. Listing IDs do not establish independent vehicle/repost groups. General discovery can include the selected families. Group assignments and parser completeness do not establish training eligibility.

Artifacts: [sampling configuration](configs/collection_pilot.json), [run instructions](docs/collection-pilot-run.md), `tests/test_collection_runner.py`, and the collection modules.

Next step: user executes the supplied command into `data/raw/pilot_batch_001/` and reports completion. Then audit saved files and evidence offline, record actual results, and choose the first modeling scope. Further live collection remains a user-run handoff.

## 4. Hurdles and resolutions

Use an ID to connect each hurdle to its investigation, fix, and later verification entry. A known limitation is not necessarily a failure already encountered in a real run.

| ID | Hurdle | Evidence | Resolution or next action | Status |
|---|---|---|---|---|
| H001 | Earlier parser missed Pakistani abbreviated prices | Historical handbook account | Add lac/lakh/crore/million conversion and broader price extraction | Fix present; current offline self-tests pass |
| H002 | Generic skipped-row messages hid extraction causes | Historical handbook account | Preserve incomplete rows, missing fields, and debug evidence | Mechanism present; fresh verification pending |
| H003 | Alphabetical URL sorting could skew the selected sample | Historical handbook account and ordered-discovery implementation | Preserve source discovery order with ordered deduplication | Mechanism present; sample representativeness still needs review |
| H004 | Production infrastructure appeared too early in the execution plan | User clarification in this conversation | Introduce a separate data/modeling pilot and defer production work | Planning correction completed |
| H005 | Parser completeness does not establish training suitability | Current completeness rule checks only four fields | Accept baseline accuracy confirmation; define identity and training eligibility rules; review new batches | Baseline accuracy confirmed by user; training suitability open |
| H006 | Titles contain model and variant details without canonical columns | Original CSV schema and source headings | URL-matched family and provisional variant extraction added in J009; reviewed catalogue still needed | Partly implemented; canonical review open |
| H007 | Missing engine displacement needs context for EVs | Three electric listings show Battery Capacity instead of Engine Capacity in inspected tables | Preserve empty displacement rather than inventing zero | Source context confirmed on three pages in J009; general applicability policy pending |
| H008 | Repeated runs counted saved/duplicate URLs against new collection limits | Original scraper control flow | Added controlled family searches, detail-attempt budgets, resume skips, and explicit request/row accounting in J010 | Implemented; offline recovery/budget tests pass; live pilot awaits user |
| H009 | Ten varied records cannot establish broad model reliability | Current sample size and lack of training results | Collect deeply within a limited, reviewed scope and evaluate held-out groups | Open |
| H010 | More data could multiply parser errors before they are discovered | Risk identified during planning | Audit early batches and resolve systematic errors before expanding | Prevention planned |
| H011 | Ignore patterns hid project records and misspelled output filenames | Workspace inspection during J006 | Replace them with explicit private-data patterns and retain trackable documentation | Fixed in working tree |
| H012 | Recommended cars also appear in structured data | Initial live-page inspection in J009 | Match structured product offer URL to the current listing; reject conflicts | Fixed; contamination tests pass |
| H013 | A displayed listing date could be mistaken for posting date | All ten inspected labels say Last Updated | Store `listing_date_type=updated`; keep collection time separate | Semantic mapping fixed; later evaluation must respect it |
| H014 | Source assembly values need quality review | Two e-tron listings report Imported and Local | Preserve both facts; examine model/assembly patterns during broader pilot | Open |

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
| D010 | Add assembly, body type, registration year, and listing date | User-selected scope; explicit date semantics and unknown values are retained | Implemented and validated on ten pages in J009; broader pilot pending |
| D011 | Exclude registration location, colour, and subjective seller condition claims | User does not want these additions; condition language is unreliable | Accepted pilot scope; listing city remains |
| D012 | Retain explicit factual registration statements with unknown meaning when needed | Registration year was present as factual text on nine sample pages | Implemented; no full-description storage or subjective condition features |
| D013 | Treat observed Last Updated dates as freshness metadata | Date labels do not establish original posting time | Implemented; use grouped collection batches for later chronological evaluation |
| D014 | The user runs every live collection command | Explicit user instruction during J010 | Persistent workflow in AGENTS.md; agent prepares commands and waits for completion |
| D015 | Use four family quotas plus general discovery for the first field pilot | Reduce dependence on one general-results page while retaining some broader examples | Target 180 complete matches, not yet collected; actual scope reviewed after results |

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
| Source accuracy confirmation | User confirms all 10 | Confirmation received after this snapshot's initial file inspection; no independent ten-row verification claimed |
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
| field_validation_2026-10-01 | 1 October 2026 | Same ten car listing IDs, extended attributes | 10 successful detail requests; 4 initial inspection and 6 manifest-recorded | 10 refreshed observations; 0 new listing IDs | Not measured | Cached HTML checksums, batch manifest, integrity audit, J009 |

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
- J009 extends verification to fifteen behavioral tests and a separate ten-page new-field sample. Registration year is present on nine pages; other agreed fields are present on all ten. These remain extraction results, not model scores.
- J010 extends offline coverage to twenty-five behavioral tests and prepares bounded family sampling with auditable outputs. The user-operated collection pilot is awaiting execution; its quotas are not results.
- A local prediction demo, trained model, measured regression result, and deployed application are pending.

## 8. Reusable story-entry template

Append completed entries to Section 3 in chronological order. Use only the fields relevant to the work; collection or training details can live in linked reports.

```markdown
### J011: <specific event or milestone>

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
