# Model comparison after source review

Date: 21 October 2026. Experiment: `m3_modeling_002_reviewed_raw_pkr_v1`.

Reran the median baseline, Ridge, Random Forest, and CatBoost on `modeling_combined_002_v2`. All candidates use the same 449 development records and split `pilot_eval_f87fae24bb5634f0`. The 114 reserved test records were excluded from training, validation, and predictions.

## Measured results

These are pooled errors from one held-out prediction per development record. Lower is better. F2 uses make, model, advertised model year, mileage, listing city, variant, fuel, transmission, displacement, assembly, and body type. Registration year is excluded.

| Candidate | Mean absolute error PKR | Median absolute error PKR | Median absolute percentage error | Fold MAE range PKR |
|---|---:|---:|---:|---:|
| Comparable median | 434,057 | 275,000 | 7.8% | 415,413-445,373 |
| Ridge F2 | 437,679 | 340,762 | 9.3% | 422,967-463,663 |
| Random Forest F2 | 280,359 | 219,247 | 5.9% | 270,540-286,549 |
| CatBoost F2 | 266,885 | 208,454 | 5.6% | 247,815-295,329 |

CatBoost F2 has the lowest pooled MAE, 38.5% below the baseline and about 4.8% below Random Forest F2. Both beat the baseline in all three folds. CatBoost beats the forest in two folds; the forest wins the third. Both remain provisional until feature experiments and demo support/error criteria are complete. The 5.6% figure is a median percentage error, not an accuracy percentage or a guarantee for every car.

| Family | Development rows | CatBoost F2 MAE PKR | Random Forest F2 MAE PKR | Baseline MAE PKR |
|---|---:|---:|---:|---:|
| Honda City | 78 | 225,172 | 297,718 | 456,455 |
| Honda Civic | 113 | 372,417 | 335,852 | 519,336 |
| Suzuki Alto | 139 | 142,225 | 156,328 | 185,507 |
| Toyota Corolla | 119 | 339,627 | 361,160 | 628,718 |

The forest does better on Civic despite CatBoost's overall lead. CatBoost MAE is PKR 400,767 on the 22 records with variants unseen in their training folds, versus PKR 259,988 on the other 427. Small subgroups remain uncertain.

F0 uses make/model/year/mileage/city. F1 adds variant. CatBoost MAE changes from PKR 332,692 with F0 to 305,299 with F1 and 266,885 with F2. Forest MAE changes from 332,546 to 291,769 to 280,359. This supports the additional groups together, but does not isolate each F2 attribute or year because year is in every set. Individual ablations remain proposed work.

User-accepted case 6 remains the largest CatBoost miss, about PKR 1,951,621. Its advertised Corolla identity and Corolla/Cross ambiguity remain recorded. A large error does not reverse a keep decision. No additional rows were removed or corrected during this run.

## Configuration and verification

The [named configuration](../configs/experiments_modeling_002_reviewed.json) preserves the preceding run's algorithm parameters, seed 42, raw-PKR target, and F0-F2 matrix. No tuning, log transform, early stopping, or new feature implementation was introduced. Fitted preprocessing learns separately within each training fold.

Completed 12 combinations, 36 fits, and 5,388 development predictions. Each fit trains on 299 or 300 rows and validates on 150 or 149. Total recorded fit time was 118.43 seconds in this environment. No fit warnings were captured. F2 forest and CatBoost predictions were all positive; Ridge F0 produced two nonpositive predictions.

Six focused model/comparison tests pass with HTTP blocked. Independently recomputed all twelve metric summaries, verified every prediction's validation fold and every fit's listing/group isolation, checked exclusions and the 100,000 km correction, and verified input/code/output fingerprints. Historical artifacts remain unchanged. No predictor was saved for inference and no test-set outcome was computed.

The historical forest MAE of PKR 311,639 and CatBoost MAE of PKR 314,476 refer to a different, unreviewed development population. Differences from these results are descriptive, not a controlled estimate of cleaning's effect: membership, one mileage input, grouping, and fold training populations changed. Reviews were prompted partly by earlier development errors, so these remain exploratory selection results. Reserved-test evaluation follows frozen candidate choices.

## Reproduction and next work

The executed run blocked HTTP around the existing offline comparison. Reproduce with a new output directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_models --dataset-dir data/processed/modeling_combined_002_v2 --evaluation-dir data/processed/modeling_combined_002_eval_v2 --config configs/experiments_modeling_002_reviewed.json --output-dir reports/pilot/m3_modeling_002_reviewed_v2
```

The completed run is in `reports/pilot/m3_modeling_002_reviewed_v1/`, including predictions, fold/subgroup metrics, fitted preprocessing details, environment, configuration, report, and manifest. The current private selection summary is `reports/pilot/model_selection.md`.

Next run named model-year and individual feature-group ablations on these same development folds, then define supported inputs and acceptable errors before freezing and saving a demo candidate. Keep registration outside all inputs and the reserved test closed during selection.

J022 update, 21 October 2026: [independent feature removals](feature-removal-experiment.md) are complete. Both references reproduce exactly. City removal improves pooled MAE but fails predeclared fold/family limits. Fuel and body type are individual removal candidates across both models; combined removal remains untested. No feature contract or reserved-test outcome changed.

J023 update, 21 October 2026: [joint fuel/body-type removal](combined-feature-removal.md) now passes both shortlisted models under unchanged safeguards. Reduced CatBoost MAE is PKR 252,692 and forest 278,531. City stays included. Reduced inference contract/support criteria remain pending; no saved predictor or reserved-test outcome was produced.
