# Processed datasets

Private derived datasets and evaluation artifacts live here. Preserve raw inputs separately and record exclusions, versions, and checksums. See [the data review](../../docs/pilot-data-review.md) and [evaluation contract](../../docs/pilot-evaluation-contract.md).

- `pilot_batch_001_v2/`: 200 normalized observations, 137 candidates, and 72 source-checked candidates, with a preparation manifest.
- `pilot_batch_001_v1/`: superseded development output; do not use for modeling.
- `pilot_batch_001_eval_v1/`: fixed split membership and shared feature contract for the 72 checked candidates. Development has 57 records and three 19-record validation folds; 15 records are reserved for a future demo test.

Commands refuse existing output directories. Use a new version when inputs or rules change. No model or fitted preprocessing exists yet.
