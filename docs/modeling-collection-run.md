# User-operated deeper modeling collection

Prepared 16 October 2026 after the first M3 comparison. No live collection has been run for this preparation.

The new [configuration](../configs/collection_modeling_002.json) targets 600 assigned parser-complete family matches: 100 each through the four broad family searches, plus 200 through older-Alto, newer-Civic, and Corolla year-tail searches. Search routes were found in saved pilot HTML. Their current availability has not been checked live.

The focused searches aim at Alto 2010/2011/2012, Civic 2022 and 2025 Multan, and Corolla 2013 and 2024 Lahore. The two city-specific routes are the available cached evidence, not nationwide year/trim samples. No exact RS/turbo/Grande quota is claimed. The collector validates family membership only; actual year/variant/city strata and quotas need offline review. Broad/focused searches may overlap, and each listing ID is assigned once within the new batch. Earlier batches may contain the same listings. Six hundred matches is a budget, not a guarantee of 600 additional usable vehicles.

Run this in PowerShell:

```powershell
Set-Location "D:\Coding Projects\pakwheels-price-predictor"
$researchContact = Read-Host "Enter your collector contact email"
.\.venv\Scripts\python.exe scraper.py --sampling-plan configs/collection_modeling_002.json --output-dir data/raw/modeling_batch_002 --ads 50 --delay 5 --contact $researchContact
```

Each invocation attempts at most 50 detail requests, including failures. The collector already saves HTML for its first 50 complete observations per invocation and every incomplete/flagged parse, so this cap retains evidence for every saved listing. Do not raise the cap for this workflow. A chunk usually needs roughly 5-10 minutes, depending on searches, responses, and resume skips. Completing 600 matches needs at least 12 chunks; failures, overlap, or exhausted searches can increase that count or leave a shortfall.

After a normal chunk, rerun the same Python command with the unchanged configuration and directory. Complete saved rows are skipped, incomplete rows can be retried, and quotas are cumulative. Run only one collector at a time. Do not add `--refresh`. Ctrl+C once saves a resumable checkpoint.

Inspect progress:

```powershell
Get-Content -LiteralPath "data/raw/modeling_batch_002/collection_summary.md"
```

A `partial` run with `run_detail_budget_reached` is expected for a normal 50-attempt chunk. If all remaining groups have exhausted searches or searches fail without progress, report the summary instead of repeatedly restarting. Stop on HTTP 401/403/429 or a `restricted` status and report it; do not resume around a restriction. The scraper can return process exit code zero after a recorded restriction, so use the console and saved status rather than exit code alone.

Everything is saved beneath `data/raw/modeling_batch_002/`: raw/clean CSVs, manifests, run summaries/logs, evidence, and diagnostics. The earlier pilot and reserved evaluation artifacts remain separate.

When finished, tell the agent to continue. Next work is offline integrity and cached-price review, actual subgroup coverage, catalogue review, and cross-batch listing/repost consolidation. Preserve the old test's status, and version any new dataset/split policy before reevaluating models.

Completion update, 20 October 2026: user-operated collection saved 608 unique IDs and 606 complete rows, with 571 assigned matches. Nine quotas were fulfilled; Civic 2025 Multan and Corolla 2024 Lahore exhausted pages at 22/25 and 24/50. Stop this unchanged plan. [Offline review and the larger comparison](modeling-batch-002-review.md) are complete; no agent-run collection occurred.
