# Pilot model artifacts

`cars_demo_v1/` contains a trusted local CatBoost research candidate trained on the 449 development records, with native model, nine-input contract, frozen support/policy, catalogue, dependency versions, development metrics, four documented cases, and hashes. It failed final demo qualification; it is not a qualified predictor release.

Use `scripts.predict --check-examples` to verify save/load behavior. General prediction serving requires the exact bundle's final evaluation to pass and is currently blocked. Generated models are private and excluded from Git.

The adopted [input contract](../../configs/predictor_inputs_v1.json) excludes fuel/body type and registration while retaining city. See [the qualification report](../../docs/demo-qualification.md) for development-only support rules, frozen error limits, final results, and one-time test status. Preserve this candidate and all earlier experiment artifacts; further selection needs an independent holdout.
