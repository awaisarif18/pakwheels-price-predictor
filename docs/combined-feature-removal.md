# Combined fuel and body-type removal

Date: 21 October 2026. Experiment: `m3_modeling_002_combined_ablation_v1`.

## Fixed experiment

The [individual removals](feature-removal-experiment.md) qualified fuel and body type for both shortlisted models. The user requested this combined check. Fit full F2 and F2 without both fields for CatBoost and Random Forest, preserving their parameters, seed 42, raw-PKR target, and training-fold-only preprocessing.

Use `modeling_combined_002_v2` and split `pilot_eval_f87fae24bb5634f0`: the same 449 development rows in three folds. Each fit trains on 299 or 300 rows and validates on 150 or 149. All 114 reserved test rows stay outside training, validation, and predictions. Keep city and all other F2 inputs. Registration remains excluded.

The configuration preserves the agreed maximum MAE increases: 1% overall, 3% in every fold, and 5% in every family. Both models must pass all limits using unrounded values. No limits or parameters were changed after seeing results.

## Measured results

| Model | Full F2 MAE PKR | Without fuel/body type MAE PKR | MAE change | Worst fold change | Worst family change | Pass |
|---|---:|---:|---:|---:|---:|---|
| CatBoost | 266,885 | 252,692 | -5.32% | -3.33% | -1.12% | Yes |
| Random Forest | 280,359 | 278,531 | -0.65% | +1.35% | +0.23% | Yes |

CatBoost improves in every fold and family. Its median absolute error is PKR 176,650 and median absolute percentage error is 5.04%. Forest's median error is PKR 216,140 and median percentage error is 5.97%; lower pooled MAE does not mean every metric improves.

| Family | Development rows | Reduced CatBoost MAE PKR | Change from full F2 | Reduced forest MAE PKR | Change from full F2 |
|---|---:|---:|---:|---:|---:|
| Honda City | 78 | 211,250 | -6.18% | 296,495 | -0.41% |
| Honda Civic | 113 | 345,736 | -7.16% | 334,694 | -0.34% |
| Suzuki Alto | 139 | 140,627 | -1.12% | 151,341 | -3.19% |
| Toyota Corolla | 119 | 322,403 | -5.07% | 361,993 | +0.23% |

The pair qualifies under the predeclared policy for both models. Recommend omitting fuel and body type from the next predictor's inputs, keeping make, model, advertised model year, mileage, listing city, variant, transmission, engine displacement, and assembly. The shared saved F0-F2 contract has not been replaced; the reduced candidate still needs its own frozen inference contract and support/error criteria. Preserve collected fuel/body-type values in source and derived data.

CatBoost remains the overall leading candidate; forest still has lower Civic MAE. These are exploratory development selection results from a fixed seed, not a final-test result or proof that fuel/body type never matter in other data. No additional removals, tuning, or new collection were performed.

## Verification and artifacts

Completed four configurations, 12 fits, and 1,796 held-out predictions. Full references reproduced the preceding reviewed run exactly, with zero prediction/PKR-metric differences. Total recorded fit time is 79.25 seconds. No fit warnings or nonpositive predictions were recorded.

All 76 behavioral tests pass with HTTP blocked. Two added tests cover the exact combined-pair configuration, rejection of mixed or unrelated removals, both omitted inputs, four-configuration reporting, retained metadata, preserved development folds, unchanged inputs, and artifact hashes. Existing independent-removal and model tests still pass.

Independent post-run checks recomputed all four summaries, all 12 fold metrics, and every removal decision. Every prediction matches development IDs, targets, groups, and folds; every fit preserves listing/group isolation. Rejected IDs stay excluded, the 100,000 km correction and accepted case 11 remain intact, city stays in model inputs, and registration remains absent. Current input/code/output hashes and historical artifact hashes match.

The existing offline runner now accepts configuration version 2 for this exact joint pair. Version 1 retains its fixed nine individual removals. The [combined configuration](../configs/ablations_modeling_002_combined.json) records settings and thresholds. Results are in `reports/pilot/m3_modeling_002_combined_ablation_v1/`, including predictions, fold/subgroup metrics and deltas, fitted details, reference checks, environment, report, and manifest.

Reproduce offline into a new output directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.ablate_features --dataset-dir data/processed/modeling_combined_002_v2 --evaluation-dir data/processed/modeling_combined_002_eval_v2 --reference-dir reports/pilot/m3_modeling_002_reviewed_v1 --config configs/ablations_modeling_002_combined.json --output-dir reports/pilot/m3_modeling_002_combined_ablation_v2
```

The completed run blocked HTTP around this runner. Existing outputs cannot be overwritten. No inference predictor was saved and no reserved-test outcome was computed. Next finalize supported scope/error criteria and the reduced candidate contract before saving and evaluating a frozen demo predictor.

J024 update, 21 October 2026: the user has [adopted the nine-input contract](predictor-input-contract.md) for the next predictor. Fuel/body type are excluded from preparation and both candidate factories; city is retained and registration excluded. All 82 tests pass and all 449 real development inputs match the combined experiment. Supported scope/error criteria and the saved predictor remain pending. Historical evaluation contracts remain unchanged.
