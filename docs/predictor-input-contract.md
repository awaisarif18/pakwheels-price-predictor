# Adopted inputs for the next predictor

Date: 21 October 2026. Contract: `cars_reduced_v1`.

The user adopted joint removal of fuel and body type after the [combined experiment](combined-feature-removal.md) passed both models. The next predictor now uses these nine ordered inputs:

1. Make
2. Model
3. Advertised model year
4. Mileage in kilometres
5. Listing city
6. Variant
7. Transmission
8. Engine displacement
9. Assembly

The [versioned declaration](../configs/predictor_inputs_v1.json) is the default for the [next-predictor input module](../pilot/predictor_inputs.py). Fuel, body type, registration year, registration gap, price, and source metadata are excluded from predictor inputs. Existing fuel-related wording within a canonical variant is preserved; this decision removes columns, not variant identity information.

## Shared training and prediction path

`prepare_predictor_input` reads only the nine selected keys before applying the existing identity, year, mileage, city, and optional-field rules. A full source row and a prediction form produce identical normalized inputs. Fuel/body-type fields can be omitted from forms entirely.

`load_predictor_development` uses the existing verified development loader, then projects its inputs to the adopted fields without changing IDs, targets, groups, or validation folds. It exposes no reserved-test option. `predictor_frame` converts these prepared inputs or prepared forms to the same ordered frame. Prepared values should not be normalized a second time, so the fixed missing-variant token remains distinct from a supplied trim.

`build_predictor_candidate` constructs either shortlisted model with these exact preprocessing/model columns. It does not select an algorithm or fit anything. Contract loading and the public helpers reject changes to the adopted version's columns, order, numerical/categorical classification, target, or missing-value conventions.

Example for future training code:

```python
from pathlib import Path
from pilot.predictor_inputs import load_predictor_development, predictor_frame

data = load_predictor_development(
    Path("data/processed/modeling_combined_002_v2"),
    Path("data/processed/modeling_combined_002_eval_v2"),
)
frame = predictor_frame(data.inputs)
# Fit build_predictor_candidate(...) separately inside each training fold.
```

For a prediction form, call `prepare_predictor_input(form, catalogue, scope)` and then `predictor_frame([prepared])`. Use the same frozen catalogue/scope as the future fitted predictor. Missing optional variant/transmission/assembly use `__MISSING__`; missing displacement stays null and becomes NaN for libraries. Zero mileage remains valid. Unknown variants, invalid required values, and out-of-scope families/years keep their existing rejection rules. Price validation stays separate.

## Measured verification and remaining work

All 82 behavioral tests pass with HTTP blocked. Six new tests cover reading only adopted keys, training/form parity, preserved normalization, missing/invalid retained values, contract drift rejection, actual nine-column fits/predictions for both trees, and development-loader membership isolation.

Offline checks on the real dataset verify all 449 development records normalize to exactly the nine values used in the successful combined experiment. Frames match its selected F2 frame, and all six reduced-model fold records declare the same ordered inputs. IDs, targets, groups, 150/150/149 folds, the 100,000 km correction, and accepted case 11 are unchanged. Both model factories select only the adopted columns. The same 114 reserved test records remain outside the development path.

The private verification record and frozen contract copy are in `reports/pilot/predictor_inputs_v1/`. Historical source/dataset/evaluation/comparison artifacts remain unchanged, including the F0-F2 contract. Collected fuel and body-type values remain preserved for provenance and future research.

This step adopts the input contract; it produces no new model score or saved predictor. Prediction support and acceptable demo errors still need to be declared before freezing the model, training/saving the demo artifact, and evaluating the reserved test. The existing development MAEs of PKR 252,692 for reduced CatBoost and 278,531 for reduced forest remain results of the combined experiment.

J025 update, 21 October 2026: [the frozen saved candidate](demo-qualification.md) was trained on 449 development rows and evaluated once on 114 test rows. Full-test MAE is PKR 257,246; only 36 rows meet frozen support, and the final demo gate fails four checks. Prediction serving is blocked. The test is now opened evidence, tracked separately from immutable historical split files. Further selection requires a new independent holdout.
