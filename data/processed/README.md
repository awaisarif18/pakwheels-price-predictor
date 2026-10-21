# Processed datasets

Private derived datasets and evaluation artifacts live here. Preserve raw inputs separately and record exclusions, versions, and checksums. See [the data review](../../docs/pilot-data-review.md) and [evaluation contract](../../docs/pilot-evaluation-contract.md).

- `pilot_batch_001_v2/`: 200 normalized observations, 137 candidates, and 72 source-checked candidates, with a preparation manifest.
- `pilot_batch_001_v1/`: superseded development output; do not use for modeling.
- `pilot_batch_001_eval_v1/`: fixed split membership and shared feature contract for the 72 checked candidates. Development has 57 records and three 19-record validation folds; 15 records are reserved for a future demo test.
- `modeling_combined_002_v1/`: historical combined dataset, with 808 preserved observations, 804 unique listings, 630 candidates, and 567 checked candidates. Includes its derived 94-label catalogue and consolidation provenance.
- `modeling_combined_002_eval_v1/`: 453 development rows in three 151-row folds and 114 reserved test rows. Earlier partitions/folds remain intact; related groups stay together. See [the larger-batch review](../../docs/modeling-batch-002-review.md).
- `modeling_combined_002_v2/`: current reviewed dataset. All 804 unique IDs remain recoverable, with 626 candidates and 563 eligible rows: 562 exact-price agreements plus one user-accepted exception. Includes frozen review decisions and the 100,000 km correction.
- `modeling_combined_002_eval_v2/`: current reviewed evaluation, with 449 development rows in 150/150/149 folds and the same 114 reserved test rows. The [reviewed comparison](../../docs/reviewed-model-comparison.md) now has 36 completed development fits; test outcomes remain closed. See [the rebuild](../../docs/reviewed-dataset-rebuild.md).

Commands refuse existing output directories. Use a new version when inputs or rules change. Initial M3 comparisons have fitted preprocessing within development folds; no saved or qualified predictor exists yet. See [the comparison](../../docs/pilot-model-comparison.md).

J025 status: membership in `modeling_combined_002_eval_v2/` is unchanged, but its 114 test rows were evaluated once for the frozen saved candidate. The final demo gate failed. Original manifests are immutable historical snapshots; the authoritative opened-test usage record is under `data/manifests/test_usage/`. See [results and next-holdout requirements](../../docs/demo-qualification.md).
