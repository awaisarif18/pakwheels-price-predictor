# Reviewed dataset rebuild

Date: 21 October 2026. Dataset: `modeling_combined_002_v2`. Evaluation: `modeling_combined_002_eval_v2`. No model training or source HTTP request was run in this step.

## Applied decisions

The user accepted cases 6-11 and excluded cases 1-5 and 12. All twelve decisions are frozen in the dataset's `manual_reviews.json` and recorded with their reasons. Raw source files and earlier datasets/reports remain preserved.

- Cases 1-5, listing IDs `12137528`, `12137467`, `12089564`, `12137385`, and `12057457`, are removed from modeling eligibility. Case 12, `12051599`, also has a manual exclusion and was already outside the candidate year range.
- Case 8, `12136988`, uses the explicitly confirmed 100,000 km. `manual_updates` retains the original 100 km and corrected value. The change is applied before cross-batch regrouping.
- Case 11, `11689890`, retains displayed PKR 2,800,000 through the exact user-accepted price pair, versus structured PKR 2,799,999. `manual_price_accepted=True` records this decision; `source_price_verified=False` still records the lack of exact agreement. It does not override unrelated eligibility rules.
- Case 6 stays with its advertised Corolla identity as the user requested, with the source Corolla/Cross ambiguity preserved in the review history. No new family mapping was invented.
- Registration year remains metadata only. All F0-F2 inputs exclude registration and registration-gap fields. Advertised model year is not relabeled as a verified manufacturing date.

## Rebuilt counts

| Output | Rows |
|---|---:|
| Preserved normalized batch observations | 808 |
| Unique listing IDs in normalized export | 804 |
| Modeling candidates | 626 |
| Exact-price-agreement eligible rows | 562 |
| Explicitly user-accepted price exception | 1 |
| Total reviewed modeling population | 563 |

The eligible population changes from 567 to 563: five previously eligible rows are excluded and one previously excluded price case is reinstated. The sixth user rejection was already excluded. Sixty-three other candidates still lack checked or accepted prices and stay outside evaluation.

| Family | Reviewed modeling rows |
|---|---:|
| Toyota Corolla | 149 |
| Honda City | 98 |
| Honda Civic | 142 |
| Suzuki Alto | 174 |

## Evaluation preservation

The parent is the larger evaluation `modeling_combined_002_eval_v1`, not the original 72-row pilot. The rebuilt split ID is `pilot_eval_f87fae24bb5634f0`.

All 114 reserved test listing IDs, targets, and F2 input values are unchanged. Every surviving parent development record retains its validation fold. Rejected IDs are absent from both partitions. The reinstated case 11 enters development only, assigned deterministically to a fold using family/global counts. Review outcomes do not select a new holdout or move previously used development records into an untouched test.

The result is 449 development rows in folds of 150, 150, and 149, plus 114 reserved test rows. Training would use 299 or 300 development rows per run. The test remains unopened for model outcomes. Rebuilding membership does not create new accuracy evidence or refresh the market period.

## Offline reproduction

These are the commands executed, with HTTP requests blocked in the verification wrapper:

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_modeling_dataset --output-dir data/processed/modeling_combined_002_v2 --report-dir reports/pilot/modeling_combined_002_v2 --parent-evaluation data/processed/modeling_combined_002_eval_v1

.\.venv\Scripts\python.exe -m scripts.prepare_evaluation --dataset-dir data/processed/modeling_combined_002_v2 --output-dir data/processed/modeling_combined_002_eval_v2 --config configs/evaluation_modeling_002_reviewed.json --catalogue data/processed/modeling_combined_002_v2/catalogue.json --scope data/processed/modeling_combined_002_v2/scope.json
```

Existing output directories cannot be overwritten. Reproductions need new dataset, report, and evaluation output directories, with evaluation input paths pointing to the reproduced dataset. Keep the same historical parent and saved review decisions to reproduce membership.

The dataset includes catalogue, scope, manual decisions, all derived observations, normalized unique listings, candidate/eligible subsets, and a manifest. The separate preparation report includes cached evidence comparisons, applied-review notes, consolidation decisions, and coverage. Manifests bind raw/configuration/code/output/report hashes and preserve the explicit price-exception count.

## Verification and next step

All 66 behavioral tests pass with HTTP blocked. The two new split checks cover a single reinstated group, no new groups, deterministic target-independent assignment, rejected-row removal, and unchanged surviving folds/holdout. Actual F0-F2 development loaders return the same 449 IDs and folds, the corrected mileage, and no registration fields. All six rejected IDs are absent; all 114 test IDs remain reserved; historical artifact hashes are unchanged.

Next rerun the fixed development comparison and the named year/feature-group experiments on this reviewed population. The earlier PKR 311,639 forest MAE and PKR 314,476 CatBoost MAE belong to the unreviewed version and must not be claimed as scores for this rebuilt dataset. No new metric or saved predictor was produced here.

J021 update, 21 October 2026: the [reviewed development comparison](reviewed-model-comparison.md) is complete. CatBoost F2 MAE is PKR 266,885, versus Forest F2 280,359 and baseline 434,057. The 114 reserved test records remain unopened for model outcomes; model-year/individual feature ablations and demo qualification remain pending.
