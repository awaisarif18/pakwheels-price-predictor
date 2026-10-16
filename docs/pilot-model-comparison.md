# First exploratory model comparison

Date: 16 October 2026. Active plan: M3. Dataset: `pilot_batch_001_v2`. Split: `pilot_eval_6988c20705512365`.

## What the comparison does

The comparison uses the 57 development listings and their three saved folds. Each run learns from 38 listings and predicts the other 19. Across the three runs, every development listing receives one held-out prediction. The 15 reserved demo-test listings are never requested for prediction or scoring.

The fixed [experiment configuration](../configs/experiments.json) compares a comparable-price median, Ridge, Random Forest, and CatBoost across F0, F1, and F2. There is one configuration per algorithm, giving 12 combinations and 36 fold fits. All use raw-PKR targets, the same seed and membership, and the existing shared input contract. There is no tuning search, log target, early stopping, or prediction clipping.

- The median uses training-only family/year medians, then family, make, and global fallbacks. Non-global groups need at least two training rows. It deliberately ignores the additional F1/F2 inputs, so its predictions match across feature sets.
- Ridge uses training-only numerical median imputation, numerical scaling, and one-hot categorical encoding. Unknown categories map to all-zero encoded columns.
- Random Forest uses the same imputation and categorical encoding without scaling.
- CatBoost receives explicit categorical strings and numerical NaN values with `nan_mode=Min`. It uses one CPU thread and writes no training files.

An entirely missing numerical training column uses the imputer's documented zero fallback for the encoded matrix. This does not change raw observations or declare missing engine displacement physically equal to zero. The current checked population has populated F0-F2 inputs.

These library behaviors follow the official [scikit-learn preprocessing guidance](https://scikit-learn.org/stable/common_pitfalls.html), [unknown-category convention](https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.OneHotEncoder.html), [imputer behavior](https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html), and [CatBoost parameter documentation](https://catboost.ai/docs/en/references/training-parameters/common).

## Reproduce offline

Use the existing environment. Modeling dependencies are separate from the collector requirements:

```powershell
Set-Location "D:\Coding Projects\pakwheels-price-predictor"
.\.venv\Scripts\python.exe -m pip install -r requirements-modeling.txt
.\.venv\Scripts\python.exe -m scripts.compare_models
```

The initial report directory is `reports/pilot/m3_batch_001_v1/`. Commands refuse existing directories. To reproduce after that run, use a new directory:

```powershell
.\.venv\Scripts\python.exe -m scripts.compare_models --output-dir reports/pilot/m3_batch_001_reproduction
```

No collection is involved. The command has no test-partition option. It checks frozen input hashes, identical feature-set membership, and group isolation before fitting. It checks input hashes again before writing results. New modeling code does not alter the frozen feature implementation or split artifact.

Each report directory contains configuration, an environment snapshot, a manifest with input/code/output hashes, predictions, fold metrics, pooled metrics, subgroup metrics, fitted preprocessing details, and `model_selection.md`. Timing and creation timestamps can vary between reproductions. Models are discarded after fold scoring; no predictor is saved or qualified for demo use.

## Interpretation and next work

MAE is the average absolute difference from the listed asking price, expressed in PKR. It is not a sale-price error or an accuracy percentage. Reports also include median absolute error, median percentage error, RMSE, fold variation, and nonpositive predictions. Subgroups cover family, variant, exact model year, city, price band, and seen/unseen variant or city, with counts.

The development data has 28 family/variant combinations. Across held-out predictions, 18 of 57 rows have a variant absent from that fold's training data, and three have an unseen city. This makes sparse-category behavior a material limitation even before scores are considered.

## Measured results

The initial run completed with HTTP requests blocked. All 12 combinations produced 57 held-out predictions each, for 684 predictions and 36 fold fits. There were no fit warnings or nonpositive predictions. Input fingerprints remained unchanged.

| Candidate | F0 MAE PKR | F1 MAE PKR | F2 MAE PKR |
|---|---:|---:|---:|
| Comparable median | 785,518 | 785,518 | 785,518 |
| Ridge | 674,946 | 661,056 | 507,766 |
| Random Forest | 561,449 | 542,106 | 495,765 |
| CatBoost | 584,872 | 560,263 | 492,904 |

All three F2 ML candidates beat the median baseline in every development fold. F2 improved pooled MAE over F1 for every ML candidate. This supports retaining the extra attributes for further experiments; it does not establish which individual attribute caused the improvement.

CatBoost F2 has the lowest pooled MAE, 37.3% below the baseline, but its advantage over Random Forest F2 is only PKR 2,861, about 0.6%. Random Forest has lower median absolute error, PKR 284,451 versus PKR 314,259, and lower median percentage error, 6.9% versus 8.5%. CatBoost beat Random Forest's MAE in two of three folds. The two remain a provisional shortlist; there is no defensible final winner on this sample. Ridge is also retained as a cheap benchmark.

CatBoost's family MAEs are PKR 367,797 for City with 13 rows, 726,395 for Civic with 14, 309,303 for Alto with 16, and 585,414 for Corolla with 14. Its Alto error is 17.6% worse than the median baseline's PKR 262,938. Random Forest F2 has lower Alto MAE, PKR 229,513. A lower overall error therefore cannot qualify every family for a demo.

For CatBoost F2, the 18 validation rows with unseen variants have MAE PKR 810,457, compared with PKR 346,341 on the other 39. These are different descriptive populations, not a controlled causal comparison.

## Largest-error review and decision

Rechecked the ten largest CatBoost F2 validation misses against their cached source pages. All 60 structured comparisons of price, year, mileage, displacement, fuel, and transmission agreed. The main visible price agreed with the URL-matched structured price on all ten pages, and cached titles retained the prepared variant wording. No new extraction correction was justified.

Six of those ten variants were absent from their training fold, and five model years were outside the training fold's same-family year range. The largest miss was a 2025 Civic RS, predicted near PKR 6.41 million versus a checked asking price of PKR 9.4 million. Its training fold contained no RS-labelled Civic and no Civic newer than 2022. A 2012 Alto VXR CNG had no same-variant training row and only 2020-2026 Altos in its training fold. These are observed coverage gaps. They do not prove the sole cause of an error or validate the seller's claims. Three reviewed misses have no demonstrated unseen-variant or year-range explanation; omitted attributes and ordinary price variation remain possible causes.

Private review evidence is in `reports/pilot/m3_batch_001_review_v1/`, bound to the experiment by hashes. The complete ranking is in [the generated report](../reports/pilot/m3_batch_001_v1/model_selection.md).

Decision: finish this initial exploratory comparison without freezing a demo candidate or opening the reserved test. Next prepare deeper scoped modeling collection, prioritizing older Alto generations, Civic RS/turbo coverage, Corolla trim/year tails, and thin variant/year/mileage combinations. The plan's roughly 500-1,500 usable scoped records is a collection budget, not a reliability guarantee. Keep the current comparison as historical development evidence; a new dataset needs new versioned membership. Individual feature-group ablations and any named target/tuning experiments remain follow-up work before final candidate qualification.

Verification: 51 behavioral tests pass with HTTP blocked, including six new modeling/comparison checks. Dependency compatibility passes `pip check`. No saved predictor, demo support, final-test outcome, live collection, or infrastructure was produced. Every live collection run remains user-operated under [AGENTS.md](../AGENTS.md).
