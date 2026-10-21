# Initial audit workspace

From the project root run:

```powershell
.\.venv\Scripts\python.exe -m scripts.audit_data
```

The command audits the preserved baseline offline and creates:

- `initial_audit.md`, regenerated from local CSV evidence.
- `identity_review.csv`, created once with all reviews pending. An existing worksheet is preserved.

For another batch, pass `--raw`, `--clean`, and a separate `--output-dir`. These are audit commands, not source-fetching commands. Numerical checks and stored parse statuses do not verify source correctness.

Complete the manual worksheet before treating identity or training eligibility as reviewed. Generated files contain source evidence and are excluded from Git.

## Model comparison

`m3_batch_001_v1/` contains the initial development-only M3 experiment ledger, predictions, metrics, fitted preprocessing details, environment, and hashes. `m3_batch_001_review_v1/` records the offline source/coverage review of the ten largest CatBoost F2 misses. The tracked [comparison note](../../docs/pilot-model-comparison.md) explains results, reproduction, and limits. No final-test score or qualified predictor exists.

`modeling_combined_002_v1/` contains the second-batch evidence review, catalogue additions, consolidation decisions, and coverage. `m3_modeling_002_v1/` contains the 453-row development comparison; `m3_modeling_002_review_v1/` records its largest-error review. See [the tracked follow-up](../../docs/modeling-batch-002-review.md). The current selection summary is `model_selection.md`; no reserved test was scored.

`modeling_combined_002_v2/` contains the rebuilt evidence/quality reports applying user decisions. `source_review_decisions_2026-10-21/` preserves the completed review worksheet. See [the rebuild record](../../docs/reviewed-dataset-rebuild.md).

`m3_modeling_002_reviewed_v1/` contains the completed reviewed comparison: 12 combinations, 36 development fits, and 449 predictions per combination. CatBoost F2 MAE is PKR 266,885; Forest F2 is 280,359; baseline is 434,057. The 114 reserved test records were not scored. See [the reviewed comparison](../../docs/reviewed-model-comparison.md).

`m3_modeling_002_ablation_v1/` contains 20 feature configurations, 60 fits, and 8,980 development predictions, plus paired reference checks, subgroup deltas, and the predeclared removal decision table. City removal improves pooled MAE but fails fold/family safeguards; fuel and body type qualify individually across both models. See [the experiment record](../../docs/feature-removal-experiment.md). No reduced schema or reserved-test outcome was produced.

`m3_modeling_002_combined_ablation_v1/` contains the four-configuration, 12-fit fuel/body-type confirmation. Both models pass the existing overall/fold/family limits: CatBoost MAE PKR 252,692 and forest 278,531. The 114 reserved test records remain unused for model outcomes. See [the combined confirmation](../../docs/combined-feature-removal.md).

`predictor_inputs_v1/` contains the adopted nine-input contract copy and verification record. All 449 real development inputs match the confirmed experiment; historical artifacts and the same 114 reserved test records remain preserved. See [the adopted input contract](../../docs/predictor-input-contract.md).

`demo_qualification_v1/` freezes the candidate, pilot limits, and 18-variant development support. `demo_test_v1/` stores the one-time final results: all-114 MAE PKR 257,246, with only 36 within support and four final criteria failing. The saved research candidate is not released for prediction serving. Current test usage is tracked in `data/manifests/test_usage/`. See [the qualification report](../../docs/demo-qualification.md).
