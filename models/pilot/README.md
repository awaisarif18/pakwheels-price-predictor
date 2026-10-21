# Pilot model artifacts

Save the selected model, fitted preprocessing, and experiment metadata here after qualification. Initial M3 candidates have been trained and scored within development folds, then discarded. No saved or qualified predictor exists yet. Generated artifacts are private and excluded from Git. See [the comparison](../../docs/pilot-model-comparison.md).

The next predictor uses the adopted [nine-input contract](../../configs/predictor_inputs_v1.json), ID `cars_reduced_v1`. Use `pilot.predictor_inputs` for shared input preparation, frames, and candidate construction. Fuel/body type and registration are excluded; city is retained. Save a copy of this contract with the future fitted artifact. See [usage and verification](../../docs/predictor-input-contract.md). Supported scope and acceptable errors remain pending.
