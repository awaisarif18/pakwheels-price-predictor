# Shared features and fixed evaluation splits

Date: 2 October 2026. Active plan milestone: M2. Input dataset: `pilot_batch_001_v2`.

## Saved population and membership

Evaluation uses the 72 source-checked candidates. The other 65 candidate records lack cached price agreement and are excluded from this comparison population. F0, F1, and F2 use identical row membership, with no feature-dependent filtering.

Split ID: `pilot_eval_6988c20705512365`. Private artifact directory: `data/processed/pilot_batch_001_eval_v1/`.

| Family | Development | Reserved demo test | Validation fold 0 | Validation fold 1 | Validation fold 2 |
|---|---:|---:|---:|---:|---:|
| Toyota Corolla | 14 | 4 | 4 | 5 | 5 |
| Honda City | 13 | 3 | 5 | 4 | 4 |
| Honda Civic | 14 | 4 | 4 | 5 | 5 |
| Suzuki Alto | 16 | 4 | 6 | 5 | 5 |
| Total | 57 | 15 | 19 | 19 | 19 |

Each development run trains on two folds, totaling 38 records, and validates on the remaining 19. Repeat for all three folds. The 15 demo-test records never enter development training or validation.

These are 72 distinct groups under the conservative possible-repost rule, which found no repeated specification clusters. That does not prove all vehicles are independent.

## Split policy and limitations

[The configuration](../configs/evaluation_pilot.json) fixes seed 42, a 20% test-group fraction, and three development folds. SHA-256 ranking of seed, phase, and group ID makes assignments deterministic and independent of input order and Python's random-library behavior. Targets never influence allocation.

Reserve the nearest whole-number 20% group quota within each family, producing 15/72 test records here, about 20.8%. Then allocate development groups across folds, retaining family coverage and balancing family/global row counts. Multi-record groups stay together even when row counts cannot be equal.

Every family needs at least one test group and a development group in each fold. Insufficient groups, duplicate listing IDs, cross-family groups, changed group membership, omitted assignments, and group leakage cause errors.

Family is the only stratification dimension. Combining family, variant, year, and city would create tiny strata. Report rare/unseen categories during later development evaluation. This split does not test generalization to newer collection periods.

The test is reserved and unopened for model outcomes. Source values were inspected during auditing and eligibility checks; no final-test prediction or metric has been computed. Three or four test records per family will produce unstable subgroup scores. Do not choose a new seed after seeing scores. If test results influence tuning, retire its untouched status in the experiment record and obtain a new independent test.

## Shared input rules

`pilot/features.py` exposes `prepare_input(row, feature_set, catalogue, scope)` for training CSV rows and future prediction forms. It returns ordered named fields without reading price or fitting anything. `prepare_target(row)` separately validates the positive PKR target.

| Set | Ordered fields |
|---|---|
| F0 | make, model, year, mileage_km, listing_city |
| F1 | F0 followed by variant |
| F2 | F1 followed by fuel, transmission, engine_cc, assembly, body_type |

- Resolve family and variant with the preparation catalogue. Preserve trims; reject unresolved variants and families outside the candidate scope.
- Require integral model year within 2010–2026 and nonnegative integral mileage. Preserve zero mileage. Reject booleans, fractions, NaN, infinity, and invalid required values.
- Require a city label and normalize whitespace/capitalization. Retain unseen city strings for later encoder handling; no city support is declared.
- Represent missing optional categories, including unspecified variant, with `__MISSING__`. This fixed input convention is neither learned imputation nor a base-trim alias.
- Keep missing displacement as `None`. Supplied displacement must be a positive integer. Preserve fuel acronyms such as PHEV and CNG.
- F0/F1 ignore optional fields they do not use. Freezing the population validates F2 on the same rows.
- Use model year directly. No derived age, registration gap, date, price-derived feature, ID, URL, group, or eligibility flag enters model inputs.

No imputer, encoder, scaler, rare-category grouping, target transform, or model has been fitted. Later fitted preprocessing must learn from each fold's 38 training records. Candidate pipelines must define unknown-category handling.

## Artifacts and reproduction

The artifact contains `splits.json`, `feature_contract.json`, frozen `catalogue.json`, `scope.json`, `config.json`, a count-based `split_report.md`, and `manifest.json`. The manifest records input/output/code hashes, counts, creation time, and reserved-test status. The split ID binds dataset bytes, preparation manifest, configuration, feature contract, and implementation versions. Existing output directories cannot be overwritten.

Reproduce offline into a new directory:

```powershell
Set-Location "D:\Coding Projects\pakwheels-price-predictor"
.\.venv\Scripts\python.exe -m scripts.prepare_evaluation --dataset-dir data/processed/pilot_batch_001_v2 --output-dir data/processed/pilot_batch_001_eval_v2
```

Identical inputs/code reproduce the same split ID and assignment bytes; creation timestamps differ. Data and raw evidence remain unchanged. No collection or new dependency is needed.

## Later model comparison

`load_evaluation_data` verifies input/artifact hashes and group isolation. It defaults to development data and returns aligned inputs, targets, IDs, groups, and fold IDs. Feature implementation and its identity/numeric dependencies must match the frozen versions.

```python
from pathlib import Path
from pilot.evaluate import load_evaluation_data

data = load_evaluation_data(
    Path("data/processed/pilot_batch_001_v2"),
    Path("data/processed/pilot_batch_001_eval_v1"),
    feature_set="F2",
)
for fold in range(3):
    train_indices = [i for i, assigned in enumerate(data.validation_folds) if assigned != fold]
    validation_indices = [i for i, assigned in enumerate(data.validation_folds) if assigned == fold]
    # Fit preprocessing/model on train_indices; score validation_indices.
```

An explicit `partition="demo_test"` is required to load the reserved test. This is workflow protection, not access control. Comparison commands should use development data; only a frozen-candidate evaluation should request the test.

Verification: 45 behavioral tests pass with HTTP blocked. They cover shared training/prediction inputs, deterministic assignments after reordering/target changes, group isolation, invalid population rejection, artifact round trips, checksum rejection, and overwrite refusal. Real F0/F1/F2 loaders agree on all 57 development IDs, targets, and folds.

Next is M3: compare the training-only median baseline, Ridge, Random Forest, and CatBoost across F0–F2 using these saved assignments. Record fold/subgroup errors in PKR and fitted preprocessing/configurations. Keep the test closed during selection. These experiments establish the workflow and guide deeper collection; they cannot establish broad prediction reliability.
