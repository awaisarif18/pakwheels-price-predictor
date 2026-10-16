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
