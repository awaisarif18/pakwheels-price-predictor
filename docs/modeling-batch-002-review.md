# Deeper modeling batch and combined dataset

Date: 20 October 2026. Stages: offline preparation and exploratory M3 reevaluation. Collection was executed by the user on 16-17 October. No source HTTP requests were made for this work.

## Collection outcome and source review

`modeling_batch_002` contains 608 unique listing IDs and 606 parser-complete rows. Nine of eleven assigned quotas were reached, totaling 571 of 600 complete family matches. Civic 2025 Multan reached 22/25 and Corolla 2024 Lahore reached 24/50 before their configured search pages ran out. The last invocation added no new IDs. No further run of this unchanged plan is needed.

Raw/clean exports agree and pass the existing integrity checks. Every one of the 608 current observations has cached HTML with a verified checksum. There are 604 visible-price/URL-matched structured-price agreements. Of 3,636 structured comparisons across price, year, mileage, displacement, fuel, and transmission, 3,634 agree and two differ.

The two disagreements are displayed versus structured price precision: one Corolla displays PKR 2,800,000 while its structured offer says 2,799,999; one 2001 City displays 850,000 while its structured offer says 849,500. The stored prices agree with the display. Keep both as unresolved source disagreements under the existing exact-agreement policy, without claiming a demonstrated parser error or inventing a replacement target. Two other listings lack a usable priced structured product and target. Raw rows and source snapshots are preserved.

The new batch yields 497 in-scope candidates with checked prices. This is lower than parser completeness because the candidate scope still requires the four families and model years 2010-2026. Search quotas enforced family matching, not model year or reviewed prediction support. Off-scope observations stay recoverable.

## Identity and consolidation

Added 37 observed variant labels only when the cached H1 exactly matches the make/model/variant/year and there is one current URL-matched product. The derived catalogue has 94 labels. Preserve the old catalogue and frozen evaluation files; the new catalogue is saved with the combined dataset. No fuzzy trim merges, catalogue-derived engine values, or prediction-support claims were added.

The combined input has 808 stored CSV observations, four repeated IDs, and 804 unique listing IDs. These are the two batches' stored snapshots, not a complete history of every fetch. `pilot/consolidate.py` retains the latest timestamp per listing, with all input observations exported separately. It never substitutes an older checked price when the latest observation lacks evidence. Conflicting family identities or conflicting observations at the same latest timestamp require rejection/review.

Possible-repost groups link exact complete specifications across all retained historical observations, as well as earlier group links. This prevents a changed mileage in a later observation from disconnecting an earlier same-specification link. Price does not enter grouping. Different IDs in one possible-repost group remain separate observations. Four two-row groups were found in the checked population; grouping is conservative evidence of similarity, not proof of the same vehicle.

| Combined output | Rows |
|---|---:|
| `observations.csv` | 808 |
| `normalized_all.csv` | 804 |
| `modeling_candidates.csv` | 630 |
| `source_checked_candidates.csv` | 567 |

There are 63 other candidates still lacking cached price agreement, primarily retained from the first pilot. Exclusion reasons overlap: 120 observations outside the candidate year range, 61 outside the four families, three missing prices, and two unresolved source disagreements. There were no historical development/test group collisions or unresolved variant labels after the observed-label extension.

| Family | Checked candidates |
|---|---:|
| Toyota Corolla | 150 |
| Honda City | 99 |
| Honda Civic | 143 |
| Suzuki Alto | 175 |

Targeted checked coverage includes Alto 2010/2011/2012 with 25/25/26 rows, Civic 2022/2025 with 25/24, and Corolla 2013/2024 with 26/25. The checked set contains 69 family/variant combinations, 34 with three or fewer rows, and 55 cities, 41 with three or fewer rows. Eight rows have unspecified variant and eight lack body type. Optional categories keep their explicit missing convention. Registration year is available on 88/567 rows and remains deferred.

## Evaluation history stays intact

One of the four repeated IDs belonged to the old reserved test. All 72 earlier checked records retain their previous development/test partition and fold, including all 15 original reserved test records. The pipeline also propagates historical membership to matching possible-repost groups. A group spanning old development and test would be quarantined before evaluation; none occurred here.

New groups receive a deterministic 20% reservation within each family. Old development groups are never relabeled as untouched test data, and old test groups never enter development. The larger frozen membership has 453 development rows, three validation folds of 151, and 114 reserved test rows. Each fold trains on 302. Split ID: `pilot_eval_bd6a4b5542b06eed`.

Twenty-two of the 453 held-out development rows have variants absent from their training fold. This population differs from the first pilot, so direct changes in average error are not a controlled learning-curve measurement. The mixed collection dates also do not establish chronological market generalization. No test predictions or scores have been requested.

## Reproduction and artifacts

Preparation uses saved files only:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_modeling_dataset
```

Default outputs are `data/processed/modeling_combined_002_v1/` and `reports/pilot/modeling_combined_002_v1/`. Existing outputs are preserved; reproductions need new `--output-dir` and `--report-dir` values. The report includes checksum-verified evidence reviews, exclusion/coverage tables, catalogue-addition evidence, and consolidation decisions. The dataset manifest binds source CSVs, collection manifests/run logs, historical evaluation, code, configuration, report, and output hashes.

Freeze evaluation using the derived catalogue and scope, not the smaller old catalogue:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_evaluation --dataset-dir data/processed/modeling_combined_002_v1 --output-dir data/processed/modeling_combined_002_eval_v1 --config configs/evaluation_modeling_002.json --catalogue data/processed/modeling_combined_002_v1/catalogue.json --scope data/processed/modeling_combined_002_v1/scope.json
```

The command requires the explicit history-preservation policy and verifies the parent evaluation manifest. Reproductions need a new evaluation output directory.

The fixed follow-up comparison uses the same algorithm parameters as the first experiment:

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_models --dataset-dir data/processed/modeling_combined_002_v1 --evaluation-dir data/processed/modeling_combined_002_eval_v1 --config configs/experiments_modeling_002.json --output-dir reports/pilot/m3_modeling_002_v1
```

Existing comparison directories cannot be overwritten. F0-F2 share identical development membership. Fitted preprocessing learns inside training folds. No collector, framework, deployment, or saved-predictor behavior was changed.

## Measured development comparison

Experiment `m3_modeling_002_raw_pkr_v1` produced 5,436 held-out predictions across 12 combinations and 36 fits. Each combination predicts the same 453 development rows once. There were no fit warnings. Ridge F0 produced two nonpositive predictions, recorded without clipping; the other combinations produced none.

| Candidate | F0 MAE PKR | F1 MAE PKR | F2 MAE PKR |
|---|---:|---:|---:|
| Comparable median | 458,508 | 458,508 | 458,508 |
| Ridge | 664,404 | 514,366 | 471,210 |
| Random Forest | 379,448 | 337,868 | 311,639 |
| CatBoost | 369,645 | 347,553 | 314,476 |

Random Forest F2 has the lowest pooled development MAE, 32.0% below the median baseline. Its median absolute error is PKR 217,640 and median absolute percentage error is 6.1%. Its fold MAEs range from PKR 270,698 to 351,043; each beats the same-fold baseline. CatBoost F2 is only PKR 2,837, about 0.9%, behind on pooled MAE, with fold MAEs from 284,283 to 339,688. These results retain both tree models as a provisional shortlist. Ridge F2 does not beat the baseline overall on this population.

| Family | Development rows | Random Forest F2 MAE PKR | Median baseline MAE PKR |
|---|---:|---:|---:|
| Honda City | 79 | 321,020 | 491,089 |
| Honda Civic | 114 | 360,288 | 538,860 |
| Suzuki Alto | 140 | 180,406 | 205,486 |
| Toyota Corolla | 120 | 412,351 | 655,917 |

Random Forest's pooled family errors are lower than baseline for all four families. This does not establish support for every trim/year/city combination. F2 helps both tree candidates beyond F1; individual feature-group ablations remain necessary before freezing demo inputs. Do not interpret the smaller error than the 57-row pilot as a controlled measure of the benefit of more training data: the population and development membership changed.

## Largest-error findings and next decision

Rechecked the ten largest Random Forest F2 errors against their selected cached snapshots and hashes. All 60 core comparisons agreed after any previously evidenced preparation correction, and all ten main prices agreed with their URL-matched offers. No new extraction correction was justified.

Four unusually low asking prices, including a 2026 Alto at PKR 300,000 and a 2014 City at PKR 295,000, are present in the source snapshots. Seller comments do not explicitly identify them as installment or down-payment ads. Their intended full-price meaning and seller truth remain unresolved; do not guess missing zeros, silently replace targets, or drop rows merely to improve validation scores.

One Corolla Hybrid G-X advertisement describes a Corolla Cross in its seller comments while the title/structured identity resolves to Corolla. This is an observed source identity ambiguity, not sufficient evidence to silently assign a new family. Another high-priced 2013 Corolla's seller explicitly defends the asking price; that does not establish its market value. The review also found one unseen variant and two unseen cities among the ten misses, with overlaps. Four other misses have no demonstrated explanation from these checks. Subjective condition claims were not added as model features.

Private evidence and classifications are in `reports/pilot/m3_modeling_002_review_v1/`. The full [generated ranking](../reports/pilot/m3_modeling_002_v1/model_selection.md) contains fold errors and all subgroup metrics.

Decision: keep this version as reproducible exploratory evidence. Resolve the flagged price-meaning/identity cases under an explicit quality policy, complete the small feature-group ablations, and define demo support/error tolerances before saving a predictor or opening the test set. A clean numerical score alone does not settle those decisions. No additional collection is required to complete that offline review.

Verification: 58 behavioral tests pass with HTTP blocked, including seven new consolidation/history checks. They cover latest-observation selection without old-price fallback, historical possible-repost links, reserved-test propagation, development/test collision quarantine, catalogue evidence, deterministic continued splits, full preparation/evaluation loading, overwrite refusal, and parent-manifest tampering. Source/export/code/report/output hashes were checked. All original 72 partitions and folds are unchanged; 114 current test IDs are absent from model predictions. No final-test outcome or qualified predictor exists.

## User review update, 21 October 2026

The user confirmed Alto listing `12137528` and City listing `12137467` are wrong entries. `configs/manual_reviews.json` now excludes them from future model populations, with raw evidence preserved. The loader refuses the historical combined development population until a new reviewed dataset/evaluation version is prepared. The results above remain historical; they were not recomputed after this decision. The other source cases are awaiting the user's keep/exclude/correct review, recorded in `reports/pilot/source_review_2026-10-21/`.

Registration year is metadata only by explicit user instruction and remains absent from every model input set. Advertised model year is not silently relabeled as a verified manufacturing date. No retraining, year ablation, or final-test scoring occurred during this review handoff. Sixty-two tests pass with HTTP blocked.

The subsequent user review accepts cases 6-11 and excludes cases 1-5 and 12. Case 8's mileage is explicitly confirmed as 100,000 km. Case 11's displayed price is accepted through a snapshot-matched manual precision exception; its source-agreement flag remains false. Decisions and original/corrected values are recorded separately. The completed worksheet is in `reports/pilot/source_review_decisions_2026-10-21/`. A new dataset/evaluation version is still required before further model work. Sixty-four tests pass with HTTP blocked; no new scores were computed.

Rebuild completion: [reviewed dataset version 2](reviewed-dataset-rebuild.md) now contains 563 eligible rows, 449 development rows, and the same 114 reserved test rows. All decisions and the mileage correction are applied. Sixty-six tests pass; models have not been retrained on version 2. The scores in this document remain historical version 1 results.

Reviewed rerun completion: [the version 2 comparison](reviewed-model-comparison.md) now reports CatBoost F2 MAE PKR 266,885 and Forest F2 280,359, against baseline 434,057 on 449 development rows. All 114 test records remain reserved. Year/individual feature ablations and demo qualification are next.
