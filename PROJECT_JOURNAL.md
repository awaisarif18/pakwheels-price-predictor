# Project journal: Pakistan vehicle price predictor

Created: 1 October 2026. Last updated: 21 October 2026.

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

| Area | Status as of 21 October 2026 | Evidence or limitation |
|---|---|---|
| Goal | Estimate advertised asking prices in Pakistan, in PKR | Separate car and motorcycle predictors are intended |
| Car collector | Sampling, persistence, main-price selection, and PHEV parsing implemented | Eighty-two offline tests pass with HTTP blocked; no live collector launched during J017-J024 |
| Initial car sample | Ten stored records, preserved with checksums | Baseline and active copies exist under `data/raw/` |
| Field collection pilot | 200 stored IDs; 199 parser-complete rows; 180 complete quota matches | Offline review produces 137 candidates and 72 with cached price agreement; J013 |
| Deeper modeling collection | User saved 608 unique IDs, 606 complete rows, and 571/600 assigned matches | Nine quotas met; two configured searches exhausted; stop unchanged plan |
| Extraction correctness audit | New batch: 608 cached pages checked; 3,634/3,636 core comparisons agree; two source price differences | Initial 108-page audit and evidenced fixes preserved; source agreement does not certify seller truth |
| Make/model/variant normalization | Derived combined catalogue preserves 94 observed labels | 37 evidence-backed additions; user keeps the advertised Corolla identity despite the preserved Corolla/Cross ambiguity |
| Dataset preparation | Reviewed v2 exports 808 observations, 804 unique IDs, 626 candidates, and 563 eligible rows | J020 applies all review decisions: 562 exact-price agreements plus one explicit user acceptance; case 8 corrected to 100,000 km |
| Motorcycle collector | Planned | Live motorcycle detail parsing has not been verified here |
| Feature selection | Adopted nine-input contract `cars_reduced_v1` for the next predictor | Fuel/body type removed from next-predictor preparation and model factories; city retained; registration excluded; historical F0-F2 preserved |
| Evaluation membership | Reviewed v2 has 449 development records in folds of 150, 150, and 149; 114 reserved test records | Split ID `pilot_eval_f87fae24bb5634f0`; surviving parent folds and all 114 test records preserved |
| Algorithm selection | Reduced CatBoost remains provisional overall leader | Joint-removal MAE PKR 252,692 versus forest 278,531; input contract adopted in J024; support/error criteria pending |
| Model training and evaluation | J023 adds four configurations, 12 fits, and 1,796 development predictions | Pair improves MAE 5.32% for CatBoost and 0.65% for forest; no final-test result or saved predictor |
| Local demo | Planned | Follows the data/modeling pilot |
| Production framework and infrastructure | Deferred | FastAPI and managed infrastructure remain future recommendations |
| Publication | Private review required before public release | Authorization and review conditions are reported in the handbook |

Next proposed work: declare supported scope/error criteria and freeze the model choice, then save and evaluate a frozen demo predictor using the adopted nine-input contract. J024 implements the user's fuel/body-type removal decision; city remains included, registration excluded, and historical F0-F2 artifacts preserved. Keep all 114 reserved test outcomes closed during selection. Live collection remains user-operated under [AGENTS.md](AGENTS.md).

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

### J011: handling Windows access denials when replacing collection logs

Date: 2 October 2026. Stage: M1 collection recovery. Status: offline fix verified; user-operated resume pending.

Reported failure: the user-run collector stopped with `PermissionError: [WinError 5] Access is denied` while replacing `runs/20261001T153413246598Z.json.tmp` with its destination JSON file. The supplied console output reported 86 stored rows and 85 parser-complete rows. These counts are user-reported here; no per-record review was performed for this fix.

Reproduction: a native Windows test held a disposable destination file open with read/write sharing allowed and delete sharing denied. The actual JSON writer failed with the identical WinError 5. Releasing that handle allowed replacement. This reproduces the file-lock mechanism; the process responsible for the user's original denial was not identified. A disposable write probe in the actual batch run directory succeeded, so permanent directory-level denial was not reproduced.

Cause addressed: JSON and CSV writers attempted replacement once and aborted on a transient access denial. Added a shared `collector/persistence.py` replacement helper with six attempts and exponential waits totaling at most 3.1 seconds. Only permission/sharing errors are retried. Persistent denial still raises, preserves the previous destination, and retains the temporary file. HTTP requests are not retried by this change.

Verification: the native Windows regression test failed before the fix and passed afterward. Additional checks verify bounded retries, preservation of existing JSON under persistent denial, and immediate propagation of unrelated filesystem failures. All 28 behavioral tests passed with live HTTP blocked. Tests used disposable files; existing batch artifacts were not rewritten. No live collector was launched.

Limitations: a permanent lock or access policy can outlast the retry window. The fix handles temporary contention and does not certify that every possible Windows access denial is resolved. No antivirus, editor, or other process is asserted to be responsible without evidence.

Next step: the user resumes with the unchanged sampling configuration and `data/raw/pilot_batch_001/`, without `--refresh`. Existing complete rows are skipped; incomplete rows can be retried. Record collection results after the user reports completion.

### J012: confirming that the user-operated field pilot met its collection targets

Date: 2 October 2026. Stage: M1 collection. Status: collection targets fulfilled; data-quality review pending.

Verification scope: read `collection_summary.md`, `manifest.json`, and the latest run's accounting. No individual source-record review, further collection, or training was performed. The summary and manifest agree on counts.

Observed results: `pilot_batch_001` has 200 stored rows and 200 unique listing IDs, with 199 parser-complete rows. Every requested quota was reached: 40 Corolla, 40 City, 40 Civic, 40 Alto, and 20 general-discovery complete matches. Those sum to 180 assigned complete matches. The other 19 complete observations remain outside those matched quotas; one stored observation is incomplete. Listing IDs still do not establish independent vehicle/repost groups.

The latest resumed run completed with no stop reason: 5 search requests, 114 detail requests, 119 successful request outcomes, 114 newly stored rows, zero refreshed rows, and 41 duplicate IDs considered. Its elapsed time was 701.564 seconds. The earlier failed run remains recorded in the manifest rather than being overwritten. The reported Windows replacement error did not stop this resumed run; no retry-occurrence count is available.

Field availability across all 200 raw rows: make/model 199 each, variant 194, model year 200, price 199, mileage 200, fuel 198, transmission 200, engine displacement 200, listing city 200, assembly 200, body type 199, listing date 200, and registration year 62. Registration-year availability is 31%; it must remain optional. Missingness alone does not establish whether the information was absent from the source or expressed in an unsupported format.

Decision: this fulfills the collection size and family-quota requirements for the field pilot. Proceed to offline integrity, identity, coverage, and source-evidence review before deciding modeling eligibility. Further collection is not needed merely to meet the existing quotas. No model reliability claim follows from parser completeness.

Artifacts: private batch summary, manifest, run logs, CSVs, and saved HTML under `data/raw/pilot_batch_001/`.

### J013: cached evidence exposes extraction errors and establishes the first candidate dataset

Date: 2 October 2026. Stage: M1 quality review and initial M2 preparation. Status: offline review/preparation complete; splits and experiments pending.

Goal: establish trustworthy field meanings, a practical first scope, and repeatable preparation before training or another collection run.

Starting point: the user's completed `pilot_batch_001` contains 200 unique listing IDs and 199 parser-complete rows. The raw/clean exports passed integrity and export-consistency checks. Actual four-family membership is 170 records, including off-target search results saved under other assignments.

Evidence review: verified checksums for 108 cached pages and compared six core fields against 107 uniquely URL-matched structured products. Of 642 comparisons, 640 matched and two differed. This measures stored/source snapshot agreement in the retained sample, not seller truth or general parser accuracy.

Problems and repairs: Civic ID 11874852 had stored PKR 3,095,000 from a recommended car. Its own visible price and matching structured offer both show PKR 4,850,000. Main-price selection now takes precedence; recommendation cards are removed from fallback text; Call for price remains missing. Haval H6 ID 12033889 had missing fuel despite an explicit PHEV value; PHEV is now parsed. Both evidenced values were repaired only in derived copies. An uncached Chery with missing fuel remains unchanged. Prado ID 12075118 remains without a target because the source says Call for price.

Implementation: added separate identity, evidence, quality, and reporting modules with a thin offline preparation command. The observed-label catalogue has four families and 57 preserved variant labels. Case/whitespace normalization does not collapse distinct trims. N/A body-type values become missing, zero mileage remains valid, and every exclusion has a reason. Possible-repost grouping excludes price and retains all rows; no multi-record clusters were found under this conservative rule.

Measured results: the candidate scope of Corolla, City, Civic, and Alto in years 2010–2026 produces 137 records: 37/36/30/34 by family respectively. Their cached-price-checked subset contains 72 records: 18/16/18/20. Sixty-five other candidates remain pending price verification. Sixty-three observations are excluded overall; overlapping reasons are year outside scope (40), family outside scope (30), and missing price (1). All 200 remain in the normalized export.

Missingness and coverage: normalized observations have five missing body types after recognizing source placeholders. Candidates have one missing body type and one unspecified variant; the 72 source-checked candidates have populated F0–F2 fields. Registration year is available for 40/137 candidates, with unknown meaning, so registration-gap features are deferred. All observed listing dates mean updated, not originally posted. There are 42 candidate family/variant combinations, of which 31 have three or fewer observations, and 17 cities, of which 12 have three or fewer observations. These counts do not support a broad reliability claim.

Development correction: an added test caught generic placeholder handling erasing the meaningful registration metadata `unknown`. Fixed normalization to apply missing-category rules only to feature categories. Marked intermediate `pilot_batch_001_v1` superseded; `pilot_batch_001_v2` is the final prepared dataset.

Verification: the three new parser regressions failed before the extraction fix and passed afterward. Five preparation tests cover raw-copy preservation, zero/placeholder/metadata semantics, trim distinctions, evidence-only repairs, scope, possible-repost grouping, and checksum rejection. All 36 behavioral tests and both original synthetic parser self-tests passed with HTTP requests blocked. Input hashes remained unchanged:

- Raw: `963ee57aa0ef61c1dac06566f393294f275a73d1bcd198f4af17c87a9e720dbc`.
- Clean: `6f6a3ad2627b6daf53b4ac635698eae54d8d90755306dd6b8de82d132947accc`.

Artifacts: `data/processed/pilot_batch_001_v2/` contains all normalized rows, candidates, source-checked candidates, and a manifest with input/output/code/configuration fingerprints. `reports/pilot/pilot_batch_001/` contains the quality report, family/year/city coverage tables, and evidence comparisons. [The tracked review](docs/pilot-data-review.md) records the contract and reproduction command.

Outcome and next work: extraction fixes and deterministic preparation are complete. F0–F2 remain comparison candidates; no fitted preprocessing, split, trained model, or model score exists. Continue M2 split/feature work and exploratory M3 comparison, then deepen collection within the measured scope before finalizing a demo. No live collection, dependency installation, or production infrastructure work occurred during this step.

### J014: shared feature preparation and frozen exploratory evaluation membership

Date: 2 October 2026. Stage: M2 feature/evaluation preparation. Status: completed; M3 comparison not run.

Goal: make training and future prediction interpret inputs identically and give every algorithm/feature comparison the same independent evaluation membership.

Starting point: `pilot_batch_001_v2` has 72 source-checked candidates. The remaining 65 candidates lack cached asking-price verification. No previous fitted preprocessing or split existed.

Implementation: `pilot/features.py` resolves identities, validates integral year/mileage/displacement, preserves zero mileage and trims, normalizes category labels, and selects only ordered F0/F1/F2 fields. The fixed `__MISSING__` token represents unspecified optional categories; numerical missingness remains `None`. Target validation is separate from prediction preparation. Registration/date/ID/provenance/group metadata do not enter model inputs. No fitted transformation was created.

Split decision: `configs/evaluation_pilot.json` fixes seed 42, a 20% group quota by family, and three development folds. `pilot/splits.py` ranks groups with SHA-256 using seed/phase/group ID. It reserves the nearest whole-number test quota per family, then balances development folds using family/global row counts. Targets and input order cannot affect assignments. Possible reposts remain together. Insufficient family groups, duplicates, cross-family groups, omissions, and leakage cause errors rather than an implicit fallback.

Measured membership: 57 development records and 15 reserved demo-test records, about 20.8% of the 72-record population. Each development fold contains 19 records, leaving 38 to train on each run. Corolla has 14 development/4 test records, City 13/3, Civic 14/4, and Alto 16/4. Every family appears in every validation fold. All 72 group IDs are distinct under the current conservative grouping rule; that does not prove independent vehicles.

Reproducibility: saved `pilot_eval_6988c20705512365` in `data/processed/pilot_batch_001_eval_v1/`. Its manifest binds exact population bytes, preparation manifest, feature contract, configuration, and implementation hashes. The artifact freezes the catalogue and scope, records split assignments and count-based reports, and refuses overwrite. `pilot/evaluate.py` loads aligned inputs, targets, IDs, groups, and fold IDs. It defaults to development data and checks artifact/data checksums, group isolation, and feature implementation versions.

Verification: added four feature tests and five split/artifact tests. The 45-test suite passed with HTTP blocked. Tests cover training/prediction agreement, target separation, zero/optional values, invalid numbers/identities, unchanged assignments after reordering or changing targets, possible-repost isolation, invalid split rejection, reproducible artifact round trips, overwrite refusal, and tampered-file rejection. Real F0/F1/F2 loaders return the same 57 development IDs, targets, and folds. Input CSVs and the preparation manifest remain unchanged.

Limits: the reserved test has only three or four records per family. Only family is stratified, so variant/year/city coverage remains sparse. Snapshot auditing and eligibility checks accessed source values, but no test prediction or score has been computed. The test is unopened for model outcomes. Future comparison commands must use development data; if test results guide tuning, retire its untouched status and obtain new independent evaluation data.

Artifacts: [evaluation contract](docs/pilot-evaluation-contract.md), fixed configuration, shared feature/split/load modules, thin `scripts/prepare_evaluation.py`, and private evaluation manifest/report. No live collection, model training, dependency installation, or production infrastructure work occurred.

Next step: begin exploratory M3 comparisons using the saved folds. Fit each candidate's imputation/encoding/scaling and baseline medians on its training fold only. Report PKR errors and subgroup counts before deciding what the deeper collection should address.

### J015: first development-only model comparison and source-backed error review

Date: 16 October 2026. Stage: M3. Status: initial comparison complete; demo candidate qualification pending.

Goal: execute the next pilot step using the saved development folds, identify whether ML improves on comparable prices, and use observed errors to guide deeper collection.

Starting point: `pilot_batch_001_v2` and split `pilot_eval_6988c20705512365` provide 57 development rows, three 19-row folds, and 15 reserved test rows. Every fold trains on 38 rows. Frozen feature construction, catalogue, scope, and memberships were retained.

Implementation: added `pilot/models.py`, `pilot/metrics.py`, `pilot/comparison.py`, `pilot/model_report.py`, a thin `scripts/compare_models.py`, and `configs/experiments.json`. A fresh estimator and its fitted preprocessing are created for each fold. The comparable baseline uses family/year, family, make, then global training medians, with minimum non-global support of two. Ridge and Random Forest use training-only imputation/one-hot encoding; Ridge also scales numerical inputs. CatBoost uses declared categorical strings, numeric NaN handling, and one CPU thread. The command exposes no final-test option, refuses existing output directories, verifies hashes/group isolation, and saves configurations, fitted preprocessing details, environment, predictions, fold/subgroup metrics, and provenance.

Experiment: `m3_initial_raw_pkr_v1`. One fixed configuration per algorithm across F0/F1/F2, producing 12 combinations, 36 fold fits, and 684 held-out predictions. Only raw-PKR targets were tried. No tuning, early stopping, log targets, clipping, or final-test scoring occurred. The baseline intentionally gives identical predictions across feature sets.

| Candidate | F0 development MAE PKR | F1 development MAE PKR | F2 development MAE PKR |
|---|---:|---:|---:|
| Comparable median | 785,518 | 785,518 | 785,518 |
| Ridge | 674,946 | 661,056 | 507,766 |
| Random Forest | 561,449 | 542,106 | 495,765 |
| CatBoost | 584,872 | 560,263 | 492,904 |

Measured findings: all three F2 ML candidates beat the baseline in all three development folds, and F2 improved pooled MAE over F1 for each algorithm. CatBoost F2 has the lowest pooled MAE, 37.3% below baseline, but is only PKR 2,861, about 0.6%, ahead of Random Forest F2. Random Forest has better median absolute error and median percentage error. CatBoost has a worse Alto MAE than baseline, PKR 309,303 versus PKR 262,938 over 16 rows, about 17.6% worse. This prevents treating aggregate improvement as four-family qualification. No final algorithm was selected.

Coverage/error review: development contains 28 family/variant combinations. Eighteen of 57 held-out listings have variants absent from their training folds; three have unseen cities. CatBoost F2 MAE is PKR 810,457 on those 18 unseen-variant rows and PKR 346,341 on the other 39. Rechecked its ten largest misses against saved pages: all 60 core structured comparisons matched, the main prices agreed with URL-matched offers, and cached headings preserved the variant wording. Six of those ten variants were absent from training and five years were outside the same-family training range. These findings overlap. The 2025 Civic RS and 2012 Alto VXR CNG illustrate missing generation/trim coverage. Three misses remain unexplained by those two checks. No new extraction repair was justified; source agreement does not establish seller truth or a causal explanation for model errors.

Environment: retained Python 3.13.7 and existing collector packages. Added a separate `requirements-modeling.txt`, tested with NumPy 2.5.3, pandas 3.0.6, SciPy 1.18.1, scikit-learn 1.9.1, and CatBoost 1.2.10. The pre-install environment snapshot is private at `data/manifests/m3_environment_before_2026-10-16.txt`; the experiment records all installed package versions. `pip check` passes.

Verification: 51 behavioral tests pass with HTTP blocked, including six new tests covering baseline support/fallbacks, train-only imputation/scaling/vocabulary, unseen categories, missing displacement, deterministic trees, PKR metrics, fresh fold estimators, group isolation, development-only loading, input preservation, output hashes, and overwrite/path refusal. The real comparison also ran with HTTP blocked. It produced no fit warnings or nonpositive predictions and preserved all input artifact fingerprints. No live collection, raw-data correction, model persistence, demo implementation, final-test outcome, or production work occurred.

Artifacts: private ledger at `reports/pilot/m3_batch_001_v1/`, private evidence/coverage review at `reports/pilot/m3_batch_001_review_v1/`, selection summary at `reports/pilot/model_selection.md`, and [tracked comparison note](docs/pilot-model-comparison.md). The run manifest binds dataset/split/configuration/code/output hashes. Models were discarded after scoring; no saved or qualified predictor exists.

Decision and next step: retain CatBoost F2 and Random Forest F2 as an exploratory shortlist, with Ridge as a cheap benchmark. Prepare deeper user-operated modeling collection around older Alto generations, Civic RS/turbo variants, Corolla trim/year tails, and thin variant/year/mileage combinations. Reevaluate on a new dataset/split version before candidate/support qualification. Individual feature-group ablations remain follow-up work. The 15 reserved test rows remain unopened for model outcomes, and no product error tolerance or reliable demo scope has been frozen.

### J016: preparing the next user-operated collection command

Date: 16 October 2026. Stage: deeper modeling collection preparation. Status: configuration prepared; live results not run.

The user requested commands to collect more data and will report completion before offline follow-up. Added `configs/collection_modeling_002.json` and [run instructions](docs/modeling-collection-run.md), using source routes found only in cached pilot HTML. The plan targets 600 assigned complete family matches: four broad 100-row searches and 200 matches across older Alto and Civic/Corolla year-tail routes. The available 2025 Civic and 2024 Corolla routes are city-specific. Family matching is enforced, but intended year/trim strata are not independently enforced by the existing runner; actual coverage remains an offline review task. Listing overlap across prior batches must be consolidated before training.

The handoff caps each invocation at 50 detail attempts. Existing first-50 evidence retention then saves every successfully parsed detail page without collector changes. Quotas accumulate in the new `data/raw/modeling_batch_002/` directory; unchanged commands resume it without refresh. Search availability, achieved quotas, new independent vehicles, source agreement, and usable-modeling counts are not measured. No live collector, refresh, fetch-missing command, or source HTTP request was launched.

Offline verification: configuration loading validates all eleven groups and a 600-match target; the existing collection-runner behavioral tests pass with HTTP blocked. No new implementation test was added for the reversible configuration change. Existing data, split membership, models, and collector code were preserved. Next action belongs to the user: run the documented command, inspect the saved summary after each chunk, and report completion or restriction/search exhaustion before offline follow-up.

### J017: reviewing the deeper batch, consolidating history, and reevaluating models

Date: 20 October 2026. Stages: offline preparation and exploratory M3. Status: completed; final candidate qualification pending.

User-reported collection: the user completed resumable chunks on 16-17 October and asked to continue offline. Saved manifests confirm 608 unique listing IDs, 606 complete rows, and 571/600 assigned matches. Nine quotas were fulfilled; Civic 2025 Multan reached 22/25 and Corolla 2024 Lahore reached 24/50 before their page budgets exhausted. The final chunk added no new listings. This is sufficient to stop the unchanged collection plan, not proof of independent usable training vehicles.

Integrity/source review: raw/clean exports agree and pass schema/numeric/duplicate checks. All 608 current rows have checksum-verified cached evidence. Visible main prices agree with URL-matched structured offers on 604. Of 3,636 structured field comparisons, 3,634 match and two prices differ. One price is displayed/stored as 2,800,000 PKR versus structured 2,799,999; another displays 850,000 versus structured 849,500. These are unresolved source representation differences, not demonstrated parser bugs. Both remain excluded under the existing exact-agreement rule. Two other rows lack a usable priced product/target. No new source repair was justified.

Implementation: added `scripts/prepare_modeling_dataset.py`, `pilot/consolidate.py`, `pilot/continued_splits.py`, and explicit evaluation/experiment configurations. Source labels require an exact cached H1 and one current product before catalogue admission. The derived catalogue adds 37 labels to the earlier 57, preserving trim wording and the old catalogue. Consolidation exports every stored observation, selects the latest timestamp per listing without older-checked-price fallback, links historical exact-specification/repost groups without using price, and quarantines development/test-history collisions. `scripts/prepare_evaluation.py` requires an explicit preservation policy for consolidated datasets and verifies the historical manifest. Existing feature semantics and frozen artifacts were retained.

Measured preparation: 808 observations become 804 unique IDs after four cross-batch repeats. There are 630 candidates and 567 candidates with cached price agreement, of which 150 are Corolla, 99 City, 143 Civic, and 175 Alto. The new batch contributes 497 candidates, all price-checked. Sixty-three other combined candidates lack checked prices. The checked set has four two-row possible-repost groups, 69 family/variant combinations, and 55 cities; 34 combinations and 41 cities have three or fewer rows. Eight rows have unspecified variants and eight have missing body type. Registration remains deferred. Raw data and original prepared/evaluation files are unchanged.

Historical evaluation: one repeated ID belonged to the old reserved test. All 72 earlier listing partitions/folds are preserved, including all 15 reserved test IDs. No historical development/test group collision occurred. New groups alone receive the seeded family-stratified 20% reservation. Split `pilot_eval_bd6a4b5542b06eed` has 453 development rows in three 151-row folds, training on 302 each time, and 114 reserved test rows. Twenty-two validation rows have unseen variants. This mixed-period population is not a chronological generalization test.

Experiment `m3_modeling_002_raw_pkr_v1`: reused the first experiment's fixed raw-PKR parameters, with no tuning, target transforms, clipping, or final-test scoring. Twelve combinations and 36 fits produce 5,436 held-out development predictions.

| Candidate | F0 development MAE PKR | F1 development MAE PKR | F2 development MAE PKR |
|---|---:|---:|---:|
| Comparable median | 458,508 | 458,508 | 458,508 |
| Ridge | 664,404 | 514,366 | 471,210 |
| Random Forest | 379,448 | 337,868 | 311,639 |
| CatBoost | 369,645 | 347,553 | 314,476 |

Random Forest F2 is 32.0% below the baseline on pooled MAE. Its family MAEs are PKR 321,020 for City over 79 rows, 360,288 for Civic over 114, 180,406 for Alto over 140, and 412,351 for Corolla over 120. Each is below the corresponding baseline. CatBoost F2 is only about 0.9% behind overall. These support a provisional tree-model shortlist, not a final algorithm or support decision. The changed population prevents interpreting the first-to-second comparison as a controlled learning curve. Ridge F0 produced two nonpositive predictions; no predictions were clipped. There were no fit warnings.

Largest-error review: all 60 core comparisons and ten main-price/offer agreements passed for the ten largest Random Forest F2 misses. Four unusually low prices are actually present in the snapshots; no explicit installment/down-payment wording was found in their seller comments. Their intended price meaning/seller truth is unresolved. Another advertisement describes Corolla Cross in comments while structured identity/title resolve to Corolla. A high-priced 2013 Corolla's seller explicitly defends the price. There are also sparse/unseen inputs and unexplained variation. These findings are preserved as review flags; no guessed zeros, silent family reassignment, or score-driven row deletion occurred. Subjective condition text was not added as a feature.

Verification: 58 behavioral tests pass with HTTP blocked, including seven new consolidation/history tests and a preparation/evaluation round trip. Checks cover latest selection, immutable observations, historical spec links, test propagation, collision quarantine, catalogue evidence, deterministic splits, output hashes, overwrite refusal, and parent tampering. Real preparation/comparison ran with HTTP blocked. Dataset/source/code/report/output fingerprints were rechecked. All 114 test IDs are absent from predictions and all 72 original partitions/folds remain intact. No live collection, saved predictor, demo implementation, final-test outcome, or production change occurred.

Artifacts: `data/processed/modeling_combined_002_v1/`, `data/processed/modeling_combined_002_eval_v1/`, `reports/pilot/modeling_combined_002_v1/`, `reports/pilot/m3_modeling_002_v1/`, `reports/pilot/m3_modeling_002_review_v1/`, updated private `model_selection.md`, and [tracked review/reproduction](docs/modeling-batch-002-review.md). Next work is flagged-label resolution, individual feature-group ablations, and declared support/error criteria before demo qualification. Keep all reserved model outcomes closed.

### J018: recording confirmed bad labels and handing source cases to the user

Date: 21 October 2026. Stage: source-quality review. Status: two exclusions recorded/enforced; other review decisions pending.

The user explicitly confirmed the previously shown 2026 Alto at PKR 300,000 and 2014 City at PKR 295,000 are wrong entries and must be excluded from future training/development. Recorded listing IDs `12137528` and `12137467` in `configs/manual_reviews.json` as user-confirmed exclusions, without inventing replacement prices or deleting source evidence. The user requested the full flagged-case list for in-chat keep/exclude decisions. Registration year is now explicitly metadata only, outside all model inputs; it is not a substitute for advertised model year or a verified manufacturing date.

Implementation: `pilot/reviews.py` validates explicit decisions, applies exclusions to new derived copies and their possible-repost groups, and rejects a stale modeling population containing excluded IDs. The evaluation loader uses that guard, so the existing combined dataset cannot accidentally be reused for another comparison without preparation of a reviewed version. Combined preparation records the review-file hash and exclusion reasons in its manifest/decision report. A keep decision never overrides other quality/scope failures.

Review handoff: private `reports/pilot/source_review_2026-10-21/` binds a twelve-case worksheet to source/experiment hashes. It includes the ten largest forest validation misses and two additional displayed-versus-structured price-precision disagreements already excluded by preparation. Two cases have a confirmed exclude decision; the remaining decisions are pending. Source links, saved prices, advertised years, mileage, cities, and review reasons are available for the user's review. A large model error alone is not treated as evidence of a wrong entry. One precision case is also outside the 2010-2026 scope.

Verification: 62 tests pass with HTTP blocked. Four new tests cover explicit exclusion/group propagation without raw/target changes, keep decisions retaining other exclusions, stale-population refusal, decision validation, and registration fields being absent from all F0-F2 model inputs. A direct offline loader check confirms the current combined development population is refused for the two rejected IDs. Raw/prepared/evaluation/experiment files remain preserved. No new dataset, fold assignment, year ablation, model training, final-test outcome, or live collection was produced. The previous metrics remain historical results that included the now-rejected labels.

Next work: accept the user's remaining review decisions, apply them in a new dataset/evaluation version with historical test protection, then continue the model-year/feature-group comparison. Registration features will not be added. Existing data counts and model scores must not be presented as results of a cleaned/retrained population.

### J019: accepting source-review decisions and the confirmed mileage correction

Date: 21 October 2026. Stage: user source-quality review. Status: decisions recorded and preparation logic verified; new dataset/evaluation/training pending.

The user accepted cases 6, 7, 8, 9, 10, and 11 and excluded cases 1-5 and 12. Recorded all twelve listing decisions in `configs/manual_reviews.json`. Case 8's initial text `100,00` was ambiguous; the user explicitly clarified 100,000 km. Its corrected mileage is therefore 100,000, with the original 100 km preserved in source evidence and `manual_updates`. Case 11 explicitly accepts displayed PKR 2,800,000 despite the structured value 2,799,999. Case 6 is retained as requested with advertised identity and the existing Corolla/Cross ambiguity note; no new family mapping was supplied or invented. Registration year remains metadata only.

Implementation: extended manual-review validation/application to support the explicitly confirmed mileage from/to correction and exact displayed/structured price-pair acceptance. Price acceptance requires matching saved evidence and does not override unrelated quality/scope exclusions. `source_price_verified` remains false for case 11; `manual_price_accepted` separately records the human decision. The population loader accepts that declared checked-by-review status without pretending exact source agreement. Corrections are applied before cross-batch regrouping. Stale populations containing excluded IDs or the old mileage are refused before modeling. Raw files and prior datasets/evaluation/metrics remain unchanged.

Verification: 64 tests pass with HTTP blocked. Added behavioral coverage for repeatable mileage correction, original-value preservation, stale-correction refusal, exact evidence-pair acceptance, missing/mismatched evidence rejection, and preservation of other exclusion reasons. A local application preview confirms six keep and six exclude decisions, the 100,000 km correction, and explicit source disagreement versus manual price acceptance. Preview counts are 626 candidates and 563 checked-or-user-accepted rows; these are not a newly generated training dataset or retrained scores.

Artifacts: `reports/pilot/source_review_decisions_2026-10-21/` preserves the completed worksheet and review-file hash; the original pending worksheet remains unchanged. No live collection, new split, model fit, year ablation, or test outcome was produced. Next work: build a reviewed dataset version and preserve the current reserved-test history before reevaluating or testing year/feature groups.

### J020: rebuilding the reviewed dataset while preserving evaluation history

Date: 21 October 2026. Stage: reviewed M2 dataset/evaluation preparation. Status: rebuild complete; retraining not run.

The user requested the rebuild after confirming the J019 decisions. Created `modeling_combined_002_v2` from the existing saved batches and `modeling_combined_002_eval_v2` using the larger v1 evaluation as its history parent. All six rejected IDs remain in preserved evidence but are absent from evaluation. Case 8 now uses 100,000 km with its original 100 km recorded in `manual_updates`. Case 11 retains displayed PKR 2,800,000 through explicit acceptance of the saved 2,799,999 structured-price disagreement; it remains distinguishable from exact source agreement. Registration stays metadata only.

Measured results: 808 normalized batch observations consolidate to 804 unique listing IDs, 626 candidates, and 563 eligible rows: 562 exact-price agreements and one manual price acceptance. The previous 567 eligible rows lose five rejected rows and gain case 11; the sixth rejection was already outside scope. Another 63 candidates still lack checked or accepted prices. Eligible families total Corolla 149, City 98, Civic 142, and Alto 174.

Evaluation preservation: split `pilot_eval_f87fae24bb5634f0` has 449 development rows in folds of 150, 150, and 149, with all 114 larger-parent reserved test IDs, targets, and F2 inputs unchanged. Every surviving historical development record keeps its validation fold. Reinstated case 11 enters development only; no reviewed result selects a new holdout. The explicit `development_only` configuration handles a single reinstatement or no new groups without reallocating history. Training would use 299 or 300 development rows per fold run.

Implementation and verification: froze the review file in the dataset, recorded creation time and separate exact-agreement/manual-acceptance counts, and clarified report eligibility wording. All 66 behavioral tests pass with HTTP blocked, including tiny/empty reinstatement populations, deterministic target-independent placement, exclusions, and preserved assignments. Actual F0-F2 loaders agree on 449 development IDs/folds, corrected mileage, and absence of registration inputs. Artifact/configuration/code/report fingerprints match; historical dataset, evaluation, and comparison hashes remain unchanged.

Artifacts and reproduction: [reviewed rebuild report](docs/reviewed-dataset-rebuild.md), `configs/evaluation_modeling_002_reviewed.json`, private dataset/evaluation directories above, and `reports/pilot/modeling_combined_002_v2/`. No live collection, model fit, new prediction, or model metric was produced. The historical forest/CatBoost scores do not apply to this reviewed population. Proposed next work is the fixed development comparison and named year/feature-group experiments, keeping reserved model outcomes closed.

### J021: rerunning the fixed model matrix on reviewed development data

Date: 21 October 2026. Stage: M3 reviewed comparison. Status: comparison complete; year/individual feature ablations and demo qualification pending.

The user requested a model rerun after the reviewed rebuild. Added `configs/experiments_modeling_002_reviewed.json` with experiment ID `m3_modeling_002_reviewed_raw_pkr_v1`, preserving the previous run's algorithm parameters, seed 42, raw-PKR target, and F0-F2 matrix. Used dataset `modeling_combined_002_v2` and split `pilot_eval_f87fae24bb5634f0`. No tuning, feature implementation, new collection, or further review decision was introduced.

Measured results: completed 12 combinations and 36 development fits on 449 listings, with 5,388 predictions. Each fit trains on 299 or 300 rows and validates on 150 or 149. Pooled MAE is PKR 434,057 for the median baseline, 437,679 for Ridge F2, 280,359 for Random Forest F2, and 266,885 for CatBoost F2. CatBoost leads overall, 38.5% below baseline and about 4.8% below forest. Both tree candidates beat baseline in all three folds; CatBoost beats forest in two. CatBoost fold MAEs range from PKR 247,815 to 295,329, versus forest 270,540 to 286,549. CatBoost median absolute error is PKR 208,454 and median absolute percentage error 5.6%; these are not accuracy guarantees. Total recorded fit time is 118.43 seconds.

Subgroups and feature evidence: CatBoost family MAEs are City PKR 225,172 on 78 rows, Civic 372,417 on 113, Alto 142,225 on 139, and Corolla 339,627 on 119. Each beats its family baseline; forest has lower Civic MAE of 335,852. CatBoost's 22 unseen-variant rows have MAE 400,767 versus 259,988 on the other 427. CatBoost F0/F1/F2 MAEs are 332,692/305,299/266,885; forest values are 332,546/291,769/280,359. These compare nested feature groups, not isolated year or individual F2 attributes. The accepted case 6 remains the largest CatBoost miss, about PKR 1,951,621; its keep decision and source identity ambiguity remain preserved.

Verification: HTTP blocked for the run and six focused model/comparison tests, all passing. Independently recomputed all twelve summaries from predictions, verified fold assignments and listing/group isolation for every fit, and confirmed no rejected or reserved-test IDs in training/validation/predictions. Confirmed corrected 100,000 km mileage, accepted case 11, identical F0-F2 membership, and no registration inputs. No fit warnings were captured. F2 tree predictions were positive; Ridge F0 produced two nonpositive predictions. Input/configuration/code/output hashes match, and historical data/evaluation/comparison artifacts remain unchanged.

Interpretation: the previous forest/CatBoost MAEs of PKR 311,639/314,476 belong to different membership and inputs. Cross-version changes are descriptive, not a controlled estimate of cleaning's effect. Reviews were prompted partly by prior development errors; the ranking remains exploratory. CatBoost and forest remain provisional, with Civic and sparse-variant tradeoffs. All 114 reserved test records stay unopened for model outcomes. Fold estimators were discarded; no saved inference predictor exists.

Artifacts: private `reports/pilot/m3_modeling_002_reviewed_v1/` contains configuration, environment, predictions, fold/subgroup metrics, fitted details, report, and manifest. Updated the private current `model_selection.md` pointer and [tracked comparison/reproduction](docs/reviewed-model-comparison.md). Next work is named model-year/individual feature-group ablations, then support/error criteria before freezing a demo candidate.

### J022: implementing and running independent feature removals

Date: 21 October 2026. Stage: M3 feature selection. Status: all 60 fits complete and independently verified; no reduced schema adopted.

The user requested implementation of the agreed experiment and suspected city has little price impact. Before results, they selected both CatBoost and Random Forest and permitted removal candidates only when MAE rises no more than 1% overall, 3% in every fold, and 5% in every family. City must pass both models to qualify across the shortlist. The same rule applies to all nine independent removals. Each removal starts from full F2, preserving make/model, reviewed rows/targets/groups/folds, seed 42, and previous model parameters. Registration remains metadata only.

Implementation: added a dedicated offline runner/configuration and paired decision/report module. Optional ordered column subsets in model/frame construction select inputs before preprocessing/estimation; default F0-F2 behavior and the frozen feature contract remain intact. Reporting retains omitted fields as metadata for subgroup analysis. Invalid, duplicate, empty, or leaking column selections are rejected. Historical reference hashes/settings are verified before fitting; both new full-F2 references must reproduce each previous prediction and PKR metric within PKR 0.01 before removals. Outputs cannot overwrite prior results or overlap inputs/raw data.

Measured run: experiment `m3_modeling_002_ablation_v1` uses `modeling_combined_002_v2` and split `pilot_eval_f87fae24bb5634f0`. Completed 20 configurations, 60 fits, and 8,980 held-out development predictions on the unchanged 449 records. Both full references reproduce exactly, with zero prediction and metric differences. Total recorded fit time is 381.32 seconds. No fit warnings or nonpositive predictions were recorded. All 114 reserved test records stay outside fits and predictions.

City evidence: removing city changes CatBoost MAE from PKR 266,885 to 262,085, down 1.80%, and forest from 280,359 to 279,668, down 0.25%. This supports limited pooled benefit under the tested settings. Neither qualifies under all predeclared limits: CatBoost fold 1 rises 3.16%, over the 3% fold cap; forest Alto MAE rises from 156,328 to 167,814, up 7.35%, over the 5% family cap. CatBoost city-removal family changes are City +4.30%, Civic -3.87%, Alto +4.81%, Corolla -5.52%. Forest changes are -1.74%, -1.46%, +7.35%, -2.20%. Keep city provisionally; no threshold was relaxed after seeing results. These fixed-seed results do not prove a causal effect or broad importance of city.

Other inputs: removing advertised model year worsens MAE 64.90% for CatBoost and 59.74% for forest, supporting its retention. Fuel and body type qualify individually for both models. CatBoost without fuel has MAE PKR 259,957 and without body type 261,597. Forest additionally qualifies mileage and assembly; its best single removal is mileage, MAE PKR 273,885. Variant, transmission, displacement, and year fail safeguards in both models. Several removals improve pooled MAE while hurting a fold/family, illustrating why pooled error alone was insufficient. Individual passes do not establish that joint removal will pass.

Verification: all 74 behavioral tests pass with HTTP blocked, including eight new tests covering actual input omission, leaking configurations, unrounded/zero-error limits, subgroup guards, reference mismatch, unchanged parameter requirements, full end-to-end assignments/group isolation, metadata retention, input preservation, and output/path protections. Independent post-run checks recompute all 20 summaries, all 60 fold metrics, and every decision from saved predictions. Every prediction's ID, target, fold, and group matches development history. Excluded IDs remain absent; case 8's 100,000 km correction and accepted case 11 remain intact. Current input/code/output and historical artifact fingerprints match.

Artifacts: `configs/ablations_modeling_002.json`; private `reports/pilot/m3_modeling_002_ablation_v1/` with predictions, fold/subgroup metrics and deltas, ordered fitted inputs, reference checks, environment, configuration, and manifest; updated current private selection summary; [tracked methods/results/reproduction](docs/feature-removal-experiment.md). No new collection, cumulative removal, model input adoption, inference predictor, or final-test result was produced. Proposed next work is a bounded joint fuel/body-type confirmation, then input/support/error decisions before saving a demo candidate.

### J023: confirming joint removal of fuel and body type

Date: 21 October 2026. Stage: M3 combined feature confirmation. Status: all 12 fits complete and independently verified; reduced inference contract/support qualification pending.

The user requested the combined check after J022 qualified fuel/body type individually for both models. Added configuration version 2 for this exact pair in the existing offline runner; version 1 retains its nine independent removals. The new configuration preserves seed 42, raw-PKR targets, full-F2 reference settings, reviewed dataset/split, and limits of 1% overall, 3% every fold, and 5% every family. City and all other F2 inputs stay included. No tuning, additional feature removal, new exclusion, source correction, or collection was introduced.

Measured results: experiment `m3_modeling_002_combined_ablation_v1` uses `modeling_combined_002_v2` and split `pilot_eval_f87fae24bb5634f0`. Four configurations and 12 fits produce 1,796 development-only predictions on the same 449 rows. Both full references reproduce exactly. CatBoost MAE falls from PKR 266,885 to 252,692, a 5.32% improvement; forest falls from 280,359 to 278,531, a 0.65% improvement. Both pass all predeclared limits. Total recorded fit time is 79.25 seconds; no fit warnings or nonpositive predictions were recorded.

CatBoost improves every fold and family: its worst fold change is -3.33% and worst family change -1.12%. Median absolute error is PKR 176,650 and median percentage error 5.04%. Its family MAEs are City PKR 211,250 on 78 rows, Civic 345,736 on 113, Alto 140,627 on 139, and Corolla 322,403 on 119. Forest's worst fold change is +1.35% and worst family change +0.23%, both within limits. Forest still has lower Civic MAE, PKR 334,694. Its median percentage error is 5.97% versus full-F2 5.95%, so not every metric improves.

Decision supported by this run: recommend omitting fuel and body type together from the next candidate's inputs. Retain make/model, advertised model year, mileage, listing city, variant, transmission, displacement, and assembly. Registration stays excluded; stored fuel/body-type evidence remains preserved. No existing F0-F2 inference contract was replaced, no predictor was saved, and no supported scope was declared. Candidate contract and demo error criteria still need to be frozen before reserved-test evaluation.

Verification: all 76 tests pass with HTTP blocked, including two new combined-configuration/end-to-end tests for exact pair validation, mixed-mode rejection, both omitted fields, retained metadata, correct counts/folds, input preservation, and output hashes. Independent post-run checks recompute all four summaries, all 12 fold metrics, and every decision. Predictions match development IDs/targets/groups/folds; every fit preserves listing/group isolation. Exclusions, case 8's 100,000 km correction, and accepted case 11 remain intact. All 114 reserved test IDs are absent from fits/predictions. Current input/code/output and historical artifact hashes match.

Artifacts: `configs/ablations_modeling_002_combined.json`, private `reports/pilot/m3_modeling_002_combined_ablation_v1/`, updated current private selection summary, and [tracked methods/results/reproduction](docs/combined-feature-removal.md). Results remain exploratory development selection evidence. No final-test outcome exists. Next work is the reduced candidate contract, support/error criteria, and saved-predictor path.

### J024: adopting the next predictor's nine inputs

Date: 21 October 2026. Stage: M3-to-demo input contract. Status: input removal adopted and verified; supported scope/error criteria and saved predictor pending.

The user explicitly requested removing fuel and body type from the next predictor after J023's joint check passed. Added versioned `configs/predictor_inputs_v1.json`, contract ID `cars_reduced_v1`, selecting make, model, advertised model year, mileage, listing city, variant, transmission, displacement, and assembly in the successful experiment's order. Registration remains excluded. Historical F0-F2 contracts, data, catalogues, and experiment artifacts remain unchanged; collected fuel/body-type values are retained as evidence.

Implementation: `pilot/predictor_inputs.py` supplies the default adopted contract, source/form normalization that reads only selected keys, a verified development-data adapter, a prepared-input frame builder, and model factories for both shortlisted trees with nine columns. Existing normalization and eligibility checks remain shared with F2, with price and metadata excluded. A loaded or supplied contract cannot silently reintroduce fields, reorder inputs, alter missing conventions, or change the target. The development adapter has no test-partition option. Algorithm choice and supported scope are separate from the input contract.

Measured verification: all 82 tests pass with HTTP blocked, including six new tests for excluded-key reads, form/training parity, retained-value/missingness rules, contract drift, actual nine-column model fits/predictions, and unchanged development membership. On the real reviewed population, every one of 449 development records matches the nine normalized inputs and frame used by the combined-removal experiment. All six reduced-model fold details declare exactly the adopted order. IDs, targets, groups, and 150/150/149 folds remain unchanged; corrected case 8 is still 100,000 km and accepted case 11 remains included. Both factories select only the adopted fields. All 114 reserved test IDs remain outside development. Historical output hashes match.

Artifacts: adopted configuration/module/tests, [input contract and usage](docs/predictor-input-contract.md), and private `reports/pilot/predictor_inputs_v1/` containing a frozen contract copy and verification record with input/code fingerprints. No live collection, new real-data model fit, new metric, saved predictor, or reserved-test outcome was produced. J023's reduced-model MAEs remain historical development evidence, not new measurements from this step. Next work is support/error criteria and frozen model choice, followed by the saved-predictor path using this contract.

## 4. Hurdles and resolutions

Use an ID to connect each hurdle to its investigation, fix, and later verification entry. A known limitation is not necessarily a failure already encountered in a real run.

| ID | Hurdle | Evidence | Resolution or next action | Status |
|---|---|---|---|---|
| H001 | Earlier parser missed Pakistani abbreviated prices | Historical handbook account | Add lac/lakh/crore/million conversion and broader price extraction | Fix present; current offline self-tests pass |
| H002 | Generic skipped-row messages hid extraction causes | Historical handbook account | Preserve incomplete rows, missing fields, and debug evidence | Mechanism present; fresh verification pending |
| H003 | Alphabetical URL sorting could skew the selected sample | Historical handbook account and ordered-discovery implementation | Preserve source discovery order with ordered deduplication | Mechanism present; sample representativeness still needs review |
| H004 | Production infrastructure appeared too early in the execution plan | User clarification in this conversation | Introduce a separate data/modeling pilot and defer production work | Planning correction completed |
| H005 | Parser completeness does not establish training suitability | Current completeness rule checks only four fields | Define explicit candidate scope, source agreement, and exclusions; J013 | Preparation implemented; reliable demo support remains unmeasured |
| H006 | Titles contain model and variant details without canonical columns | Original CSV schema and source headings | URL-matched extraction and four-family observed-label catalogue; J009/J013 | Candidate identities implemented; broader catalogue remains open |
| H007 | Missing engine displacement needs context for EVs | Three electric listings show Battery Capacity instead of Engine Capacity in inspected tables | Preserve empty displacement rather than inventing zero | Source context confirmed on three pages in J009; general applicability policy pending |
| H008 | Repeated runs counted saved/duplicate URLs against new collection limits | Original scraper control flow | Added controlled family searches, detail-attempt budgets, resume skips, and explicit request/row accounting in J010 | Implemented; offline tests pass and user-run pilot completed |
| H009 | Ten varied records cannot establish broad model reliability | Current sample size and lack of training results | Collect deeply within a limited, reviewed scope and evaluate held-out groups | Open |
| H010 | More data could multiply parser errors before they are discovered | J013 found a recommendation price and missing PHEV fuel | Fixed both demonstrated extraction issues before deeper collection | First-batch review completed; continue source checks on future batches |
| H011 | Ignore patterns hid project records and misspelled output filenames | Workspace inspection during J006 | Replace them with explicit private-data patterns and retain trackable documentation | Fixed in working tree |
| H012 | Recommended cars also appear in structured data | Initial live-page inspection in J009 | Match structured product offer URL to the current listing; reject conflicts | Fixed; contamination tests pass |
| H013 | A displayed listing date could be mistaken for posting date | All ten inspected labels say Last Updated | Store `listing_date_type=updated`; keep collection time separate | Semantic mapping fixed; later evaluation must respect it |
| H014 | Source assembly values need quality review | Two e-tron listings report Imported and Local | Preserve both facts; examine model/assembly patterns during broader pilot | Open |
| H015 | Windows denied replacement of a run log | User-run WinError 5; native file-lock regression reproduces it | Bounded retries for permission/sharing denials in JSON and CSV replacement; J011 | Offline fix verified; resumed user run completed in J012 |
| H016 | Price fallback read a recommended car's price | Cached Civic 11874852: stored 3,095,000 versus own visible/structured 4,850,000 PKR | Prefer main price box, isolate fallback text, preserve Call for price; repair derived copy; J013 | Fixed; three parser regressions pass |
| H017 | Fuel pattern omitted PHEV | Cached Haval 12033889 explicitly identifies PHEV | Extend fuel parsing; repair only evidence-backed copy; J013 | Fixed; uncached missing fuel remains unresolved |
| H018 | Generic placeholder handling erased meaningful unknown registration semantics | Preparation regression failed during development | Restrict category missingness rules; supersede v1 with v2; J013 | Fixed; metadata preservation test passes |
| H019 | Checked population is too small for stable family-level evaluation | J014 leaves only 3–4 reserved test groups per family and 38 training records per fold | Treat comparisons as exploratory, report counts, and deepen coverage before demo claims | Open; fixed splits do not solve the sample-size limit |
| H020 | Aggregate improvement hides subgroup and generation gaps | J015: CatBoost F2 improves overall MAE by 37.3%, but Alto MAE is 17.6% worse than baseline; large misses include unseen trims and out-of-training-range years | Deepen scoped coverage and reevaluate support; do not qualify all four families from pooled MAE | Open; observed in exploratory development evaluation |
| H021 | Recollection could leak earlier reserved vehicles into development | Four repeated IDs in J017, including one reserved test ID | Latest-observation consolidation preserves history and groups; collisions quarantine | Implemented and verified; all prior partitions/folds unchanged |
| H022 | Source agreement does not establish full-price meaning or correct seller identity | J017 largest errors include source-confirmed unusually low prices and Corolla/Cross contradiction | J019 decisions applied in J020: six rejects, six keeps, explicit mileage correction and price acceptance; preserve source ambiguity | Review decisions implemented; no final candidate qualified |

When a hurdle is solved, record the actual code/data change, date, verification, and story entry. Do not change `Open` to `Resolved` merely because a proposed fix has been written down.

## 5. Decision register

| ID | Decision | Reason | Status and revisit point |
|---|---|---|---|
| D001 | Predict advertised asking price in PKR | Source data contains listing prices, not verified transactions | Accepted scope |
| D002 | Start with a data/modeling pilot before production work | Data contracts and model evidence need to guide the application | Accepted execution sequence |
| D003 | Reuse the current scraper and change it incrementally | Existing collection logic works; the next changes should solve demonstrated needs | Accepted pilot approach |
| D004 | Use separate car and motorcycle predictors | Different identities, schemas, and price distributions | Planned implementation; evaluate each independently |
| D005 | Compare a median baseline, Ridge, Random Forest, and CatBoost | Test several useful modeling approaches with manageable experimental cost | Initial F0–F2 matrix completed in J015; no final winner selected |
| D006 | Preserve variants, raw observations, and exclusion reasons | Avoid hidden identity loss and make preparation reproducible | Implemented in J013; continue preserving versions |
| D007 | Keep preprocessing reusable between training and prediction | Prevent a demo from interpreting inputs differently from the trained model | Shared inputs implemented in J014; fold pipelines in J015; saved-predictor parity remains |
| D008 | Build a local saved-predictor demo before large training | Verify the complete workflow at modest cost | Planned; CLI then a small local UI |
| D009 | Reassess framework and infrastructure after pilot results | Actual workflows, latency, memory, and durability needs remain unknown | Deferred; production handover milestone |
| D010 | Add assembly, body type, registration year, and listing date | User-selected scope; explicit date semantics and unknown values are retained | Implemented in J009; broader missingness/semantics reviewed in J013 |
| D011 | Exclude registration location, colour, and subjective seller condition claims | User does not want these additions; condition language is unreliable | Accepted pilot scope; listing city remains |
| D012 | Retain explicit factual registration statements with unknown meaning when needed | Registration year was present as factual text on nine sample pages | Implemented; no full-description storage or subjective condition features |
| D013 | Treat observed Last Updated dates as freshness metadata | Date labels do not establish original posting time | Implemented; use grouped collection batches for later chronological evaluation |
| D014 | The user runs every live collection command | Explicit user instruction during J010 | Persistent workflow in AGENTS.md; agent prepares commands and waits for completion |
| D015 | Use four family quotas plus general discovery for the first field pilot | Reduce dependence on one general-results page while retaining some broader examples | All 180 assigned complete matches obtained in J012; quality review in J013 |
| D016 | Prepare four-family candidates in years 2010–2026, retaining all observed cities | Narrow older sparse generations and keep enough observations for initial experiments | Provisional preparation scope in J013; predictor support remains empty |
| D017 | Separate price-checked candidates from other candidates | A demonstrated main-price error warrants conservative initial experiments | 72 source-checked and 65 other candidates in J013; expand evidence before reliability claims |
| D018 | Defer registration timing features | Only 40/137 candidates contain registration year and its meaning is unknown | Keep the fact/provenance; reassess only with interpretable evidence and validation |
| D019 | Freeze family-stratified group splits with seed 42 before modeling | Every algorithm/feature set needs identical membership without target-driven allocation | Implemented in J014; 57 development/15 test; retire untouched status if test guides tuning |
| D020 | Share unfitted feature rules and explicit missing conventions across training/prediction | Avoid input drift, silent trim substitutions, and price/metadata leakage | Implemented in J014; fitted preprocessing remains inside future training folds |
| D021 | Run one fixed raw-PKR configuration per algorithm before tuning | Establish a bounded initial comparison without selecting lucky trials or using final-test outcomes | Implemented in J015; any later trials need named configurations |
| D022 | Keep the M3 shortlist provisional and deepen coverage before demo qualification | Tiny overall CatBoost/Forest difference and worse Alto baseline comparison do not support a final algorithm/support decision | Accepted after J015; reserved test stays closed |
| D023 | Select the latest observation per ID and preserve historical grouping/evaluation status | Cross-batch repeats must not double-count vehicles or move old development into an untouched test | Implemented in J017; original artifacts preserved |
| D024 | Keep suspicious source-confirmed prices and identity contradictions visible for explicit review | A large validation error is not proof of a parser mistake or permission to invent a target | J017 flags retained; quality/candidate policy pending |
| D025 | Exclude user-confirmed bad listing IDs from future model populations while preserving evidence | J018 initial rejects expanded to six explicit rejects in J019 | Persistent review file and preparation/loader enforcement implemented; reviewed dataset/evaluation rebuilt in J020 |
| D026 | Keep registration year as metadata only, separate from all model inputs | Explicit user instruction in J018; model year and registration are different facts | Accepted; registration/registration-gap features excluded rather than awaiting an F3 experiment |
| D027 | Preserve the larger evaluation's holdout and surviving folds during the reviewed rebuild | Review outcomes must not move used development records into an untouched test | Implemented in J020; reinstated case 11 enters development only; 114 test records unchanged |
| D028 | Use predeclared 1% overall, 3% per-fold, and 5% per-family MAE limits for individual removals on both trees | User accepts a small tradeoff for fewer inputs; subgroup regressions must remain bounded | J022 complete: city does not qualify; fuel/body type qualify individually; joint confirmation follows in D029 |
| D029 | Confirm fuel/body-type removal together under unchanged safeguards | Individual removals do not establish joint behavior; explicit user request | J023 passes on both models; user adopts the input contract in D030/J024; support criteria still pending |
| D030 | Adopt nine predictor inputs, excluding fuel/body type and registration | Explicit user instruction after successful combined confirmation | J024 implements `cars_reduced_v1` shared normalization/frames/factories; support/error criteria and saved predictor still pending |

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
| pilot_batch_001 | 1-2 October 2026 | Four family quotas plus general discovery | Latest run: 5 search and 114 detail requests, all successful; earlier failed run retained | 200 cumulative rows; 199 complete; 180 complete quota matches | 137 candidate groups; 72 source-checked groups under conservative exact-specification rule | J012 collection accounting; J013 cached evidence and derived dataset v2 |
| modeling_batch_002 | 16-17 October 2026 | Four broad searches and targeted year/city gaps | 14 user-run chunks; 293 search and 627 detail requests | 608 cumulative IDs; 606 complete; 571 complete quota matches | 497 checked candidates before cross-batch consolidation; joint groups in J017 | Saved collection manifests/logs, full current-row cached evidence, combined dataset and review |

For future batches add discovery/detail request counts, duplicates, access stops, ordinary failures, incomplete rows, exclusion counts, review sample size, actual discrepancies, elapsed time, and dataset checksum. Distinguish newly added rows from cumulative totals.

### Model experiment ledger

J015 records the first model experiment over 57 development listings; J017 records the larger comparison over 453; J021 reruns the fixed matrix on 449 reviewed development listings. Metrics below are pooled held-out development errors for each labeled dataset, not final-test results.

When experiments run, record:

| Experiment ID | Dataset/split | Features | Model and configuration | Validation MAE PKR | Final test MAE PKR | Result |
|---|---|---|---|---|---|---|
| m3_initial_raw_pkr_v1 / median_F0 | pilot_batch_001_v2 / pilot_eval_6988c20705512365 | F0 grouping subset | Training-only comparable median; minimum group size 2 | 785,518 | Not run | Baseline; identical predictions for F1/F2 |
| m3_initial_raw_pkr_v1 / ridge_F2 | Same frozen dataset/split | F2 | Ridge alpha 10, SVD; fold-only pipeline | 507,766 | Not run | Cheap benchmark retained |
| m3_initial_raw_pkr_v1 / random_forest_F2 | Same frozen dataset/split | F2 | 300 trees, minimum leaf 2, seed 42 | 495,765 | Not run | Exploratory shortlist |
| m3_initial_raw_pkr_v1 / catboost_F2 | Same frozen dataset/split | F2 | 300 iterations, depth 4, learning rate 0.05, RMSE, seed 42 | 492,904 | Not run | Lowest pooled MAE; Alto gap blocks broad qualification |
| m3_modeling_002_raw_pkr_v1 / median_F0 | modeling_combined_002_v1 / pilot_eval_bd6a4b5542b06eed | F0 grouping subset | Same median parameters as initial comparison | 458,508 | Not run | Larger-population baseline |
| m3_modeling_002_raw_pkr_v1 / ridge_F2 | Same larger dataset/split | F2 | Same fixed Ridge configuration | 471,210 | Not run | Does not beat baseline overall |
| m3_modeling_002_raw_pkr_v1 / random_forest_F2 | Same larger dataset/split | F2 | Same fixed forest configuration | 311,639 | Not run | Provisional lowest pooled MAE; labels/support pending |
| m3_modeling_002_raw_pkr_v1 / catboost_F2 | Same larger dataset/split | F2 | Same fixed CatBoost configuration | 314,476 | Not run | Provisional close alternative |
| m3_modeling_002_reviewed_raw_pkr_v1 / median_F0 | modeling_combined_002_v2 / pilot_eval_f87fae24bb5634f0 | F0 grouping subset | Same fixed median configuration | 434,057 | Not run | Reviewed population baseline |
| m3_modeling_002_reviewed_raw_pkr_v1 / ridge_F2 | Same reviewed dataset/split | F2 | Same fixed Ridge configuration | 437,679 | Not run | Does not beat baseline overall |
| m3_modeling_002_reviewed_raw_pkr_v1 / random_forest_F2 | Same reviewed dataset/split | F2 | Same fixed forest configuration | 280,359 | Not run | Provisional alternative; lower Civic MAE |
| m3_modeling_002_reviewed_raw_pkr_v1 / catboost_F2 | Same reviewed dataset/split | F2 | Same fixed CatBoost configuration | 266,885 | Not run | Lowest pooled reviewed development MAE; qualification pending |
| m3_modeling_002_ablation_v1 / catboost_without_fuel | modeling_combined_002_v2 / pilot_eval_f87fae24bb5634f0 | F2 minus fuel | Same fixed CatBoost configuration | 259,957 | Not run | Best CatBoost single removal; passes safeguards; no schema adopted |
| m3_modeling_002_ablation_v1 / random_forest_without_mileage_km | Same reviewed dataset/split | F2 minus mileage | Same fixed forest configuration | 273,885 | Not run | Best forest single removal; qualifies for this model only |
| m3_modeling_002_combined_ablation_v1 / catboost_without_fuel_and_body_type | modeling_combined_002_v2 / pilot_eval_f87fae24bb5634f0 | F2 minus fuel/body type | Same fixed CatBoost configuration | 252,692 | Not run | Passes overall/fold/family limits; reduced candidate recommended |
| m3_modeling_002_combined_ablation_v1 / random_forest_without_fuel_and_body_type | Same reviewed dataset/split | F2 minus fuel/body type | Same fixed forest configuration | 278,531 | Not run | Passes limits; lower Civic MAE than reduced CatBoost |

Include fold variability, median error, subgroup counts/errors, training time, and artifact references in the associated story entry. Label exploratory, selected, rejected, and superseded experiments explicitly. A final-test metric is `Not run` until the frozen candidate is evaluated.

### Demonstrated milestones

- Working collection logic and ten stored records are available.
- A production architecture reference and an active pilot plan have been written.
- The workspace is organized, the initial sample is preserved, and offline audit/review files are generated.
- Six behavioral tests and both existing parser self-tests pass in the current environment.
- J009 extends verification to fifteen behavioral tests and a separate ten-page new-field sample. Registration year is present on nine pages; other agreed fields are present on all ten. These remain extraction results, not model scores.
- J010 extends offline coverage to twenty-five behavioral tests and prepares bounded family sampling with auditable outputs. The user-operated collection pilot is awaiting execution; its quotas are not results.
- J012 records completion of all field-pilot quotas. J013 reviews cached evidence, fixes two extraction issues, and exports versioned candidate datasets; thirty-six behavioral tests and both parser self-tests pass offline.
- J014 implements shared F0–F2 preparation and freezes 57 development/15 test records with three 19-record folds. Forty-five behavioral tests pass with HTTP blocked; no model metrics exist.
- J015 runs 12 development comparisons with training-fold-only preprocessing and reviews the largest misses. Best pooled MAE is PKR 492,904, with sparse coverage and an Alto subgroup regression. Fifty-one behavioral tests pass; final test remains unopened.
- J017 consolidates the deeper user batch into 567 checked candidates, preserves historical evaluation, and compares 12 combinations on 453 development rows. Random Forest F2 MAE is PKR 311,639; source-price/identity questions remain before qualification. Fifty-eight tests pass and test outcomes remain unopened.
- J020 applies all twelve user review decisions in a new 563-row eligible population: 449 development and the same 114 reserved test records. Case 8 is corrected to 100,000 km; case 11 has explicit price acceptance. Sixty-six tests pass; reviewed-v2 training and scores remain pending.
- J021 completes the reviewed 12-combination comparison with 36 fits. CatBoost F2 leads with MAE PKR 266,885 versus Forest 280,359 and baseline 434,057. Six focused tests and independent prediction/metric/isolation checks pass; all reserved-test outcomes remain unopened.
- J022 completes 60 feature-removal fits and 8,980 predictions with exact full-reference reproduction. City lowers pooled MAE but fails fold/family safeguards; fuel/body type qualify individually on both models. Seventy-four tests and independent metric/isolation/decision checks pass. No reduced schema or reserved-test outcome is produced.
- J023 confirms joint fuel/body-type removal in 12 fits and 1,796 development predictions. CatBoost MAE is PKR 252,692 and forest 278,531; both pass unchanged safeguards. Seventy-six tests and independent checks pass. Reduced candidate contract/support and saved predictor remain pending; test outcomes stay closed.
- J024 adopts the nine-input contract for the next predictor, excluding fuel/body type and registration while retaining city. Eighty-two tests pass; all 449 real development inputs match the confirmed experiment. No new real-data fit, metric, saved predictor, or test outcome was produced.
- A local prediction demo, saved qualified predictor, final-test result, and deployed application are pending.

## 8. Reusable story-entry template

Append completed entries to Section 3 in chronological order. Use only the fields relevant to the work; collection or training details can live in linked reports.

```markdown
### J025: <specific event or milestone>

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
