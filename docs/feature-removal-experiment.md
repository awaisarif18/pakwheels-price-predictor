# Independent feature-removal experiment

Date: 21 October 2026. Experiment: `m3_modeling_002_ablation_v1`.

## Question and agreed policy

The user suspects listing city has little effect on predictions. Test that hypothesis alongside eight other independent feature removals. This measures predictive usefulness conditional on the other inputs, not a causal effect on market prices.

Use the reviewed `modeling_combined_002_v2` dataset and split `pilot_eval_f87fae24bb5634f0`: 449 development rows and 114 reserved test rows. Each fit trains on 299 or 300 development records and validates on 150 or 149. Reserved-test outcomes remain closed.

Run both shortlisted models with the preceding comparison's parameters, seed 42, raw-PKR target, CPU/thread settings, and training-fold-only preprocessing. First refit full F2 and require its individual predictions and PKR metric differences to be no more than PKR 0.01 from the saved reviewed comparison. Stop on a mismatch before interpreting removals.

Then independently remove listing city, advertised model year, mileage, variant, fuel, transmission, engine displacement, assembly, or body type. Every removal starts from full F2. Keep make/model in every configuration. Registration remains outside all model inputs. Do not change row membership, targets, grouping, scope, or user review decisions.

The user selected these maximum MAE increases, evaluated without rounding against each model's own full reference:

| Check | Maximum increase |
|---|---:|
| Overall | 1% |
| Every fold | 3% |
| Every family | 5% |

All three checks must pass for a feature to become a removal candidate for that model. City qualifies across the shortlist only if both models pass. Small city subgroup results remain diagnostic. Passing individual removals do not qualify a combination of removals; no reduced schema is automatically adopted.

## Implementation and reproducibility

The dedicated runner selects an ordered subset of the existing F2 contract before preprocessing/model fitting. Reporting still retains city and other metadata when excluded from model inputs. The existing F0/F1/F2 matrix and saved dataset/evaluation contracts remain unchanged.

The command validates historical artifact hashes, exact model settings, and development membership. It refuses existing output directories and paths overlapping raw data or input artifacts. A completed run saves predictions, fold/subgroup metrics and reference deltas, the decision table, ordered inputs and fitted details, reference checks, configuration, dependency versions, timings, and input/code/output hashes. No inference predictor is saved.

The [configuration](../configs/ablations_modeling_002.json) fixes experiment order, models, and limits. Run offline from the project root:

```powershell
.\.venv\Scripts\python.exe -m scripts.ablate_features --dataset-dir data/processed/modeling_combined_002_v2 --evaluation-dir data/processed/modeling_combined_002_eval_v2 --reference-dir reports/pilot/m3_modeling_002_reviewed_v1 --config configs/ablations_modeling_002.json --output-dir reports/pilot/m3_modeling_002_ablation_v1
```

Use a new output directory for reproduction. The executed run blocks HTTP around this runner. Historical reports and source data remain preserved.

## Verification

All 74 behavioral tests pass with HTTP blocked. New tests cover estimator/preprocessor column omission, invalid or leaking columns, invalid configurations, unrounded limit boundaries including zero reference error, fold/family safeguards, reference reproduction failures, parameter drift before fitting, preserved input bytes, every development assignment, group isolation, metadata retention, overwrite/path protection, and output checksums. Existing comparison, preprocessing, and input-contract tests still pass.

## Measured results

Completed all 20 configurations and 60 fits, producing 8,980 development-only predictions. Both full references reproduced the previous predictions and PKR metrics exactly, with zero differences. Total recorded fit time was 381.32 seconds. No fit warnings or nonpositive predictions were recorded.

### City hypothesis

| Model | Full F2 MAE PKR | Without city MAE PKR | Overall change | Safeguard result |
|---|---:|---:|---:|---|
| CatBoost | 266,885 | 262,085 | -1.80% | Fold 1 increases 3.16%, above the 3% limit |
| Random Forest | 280,359 | 279,668 | -0.25% | Alto increases 7.35%, above the 5% family limit |

Removing city improves pooled MAE slightly for both models, supporting the intuition that its overall benefit is limited under these settings. Neither model passes all predeclared safeguards. Keep city provisionally; the thresholds were not relaxed after observing results. This does not establish that city is essential or irrelevant in the wider market.

| Family | Rows | CatBoost MAE change without city | Forest MAE change without city |
|---|---:|---:|---:|
| Honda City | 78 | +4.30% | -1.74% |
| Honda Civic | 113 | -3.87% | -1.46% |
| Suzuki Alto | 139 | +4.81% | +7.35% |
| Toyota Corolla | 119 | -5.52% | -2.20% |

CatBoost fold MAE changes without city are +1.73%, +3.16%, and -9.08%. Forest changes are -2.46%, +0.88%, and +0.92%. These differences explain why a pooled improvement alone does not meet the agreed policy.

### All independent removals

| Removed feature | CatBoost MAE PKR | Change | Forest MAE PKR | Change | Passes both models |
|---|---:|---:|---:|---:|---|
| Listing city | 262,085 | -1.80% | 279,668 | -0.25% | False |
| Model year | 440,104 | +64.90% | 447,858 | +59.74% | False |
| Mileage | 268,212 | +0.50% | 273,885 | -2.31% | False |
| Variant | 275,864 | +3.36% | 305,895 | +9.11% | False |
| Fuel | 259,957 | -2.60% | 280,457 | +0.04% | True |
| Transmission | 276,777 | +3.71% | 284,459 | +1.46% | False |
| Engine displacement | 287,070 | +7.56% | 278,804 | -0.55% | False |
| Assembly | 268,810 | +0.72% | 280,763 | +0.14% | False |
| Body type | 261,597 | -1.98% | 277,925 | -0.87% | True |

Fuel and body type pass individually for both models. CatBoost qualifies those two only. Forest additionally qualifies mileage and assembly. Neither model qualifies removal of year, variant, transmission, displacement, or city under all safeguards. Removing year worsens MAE by 64.90% for CatBoost and 59.74% for forest, supporting retention of advertised model year.

The best observed single-removal CatBoost result is without fuel, MAE PKR 259,957; the best forest single-removal result is without mileage, MAE PKR 273,885. These are development selection results, not newly qualified predictors.

Independent post-run checks recomputed all 20 summaries, all 60 fold metrics, and every removal decision from the saved predictions. Every prediction matches the assigned development ID, target, fold, and group; every fit preserves listing/group isolation. All rejected IDs and all 114 test IDs are absent. The 100,000 km correction and accepted case 11 remain intact. Current input/code/output and historical artifact hashes match.

Next propose a bounded confirmation experiment removing fuel and body type together, compared with unchanged F2 on the same development folds. Individual passes do not establish a combined pass. Decide the final input schema and demo support/error criteria only after confirmation. No combined removal, saved predictor, or reserved-test outcome was produced here.

J023 update, 21 October 2026: [joint fuel/body-type removal](combined-feature-removal.md) now passes both shortlisted models under unchanged safeguards. Reduced CatBoost MAE is PKR 252,692 and forest 278,531. City stays included. Reduced inference contract/support criteria remain pending; no saved predictor or reserved-test outcome was produced.
