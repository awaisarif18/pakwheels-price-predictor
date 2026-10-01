# Run the field collection pilot

Prepared 1 October 2026. Collection execution belongs to the user, as recorded in [AGENTS.md](../AGENTS.md). Code preparation and verification are complete; this batch has not been run by the agent.

## What this batch is for

The next stage of [the active pilot plan](plans/DATA_MODELING_PILOT_PLAN.md) needs enough varied source examples to measure field availability, review vehicle identities, and choose a modeling scope. This is still collection research. No family is declared supported by a predictor.

The [sampling configuration](../configs/collection_pilot.json) targets:

| Search | Target complete matches | Maximum detail attempts | Maximum search pages per run |
|---|---:|---:|---:|
| Toyota Corolla | 40 | 55 | 5 |
| Honda City | 40 | 55 | 5 |
| Honda Civic | 40 | 55 | 5 |
| Suzuki Alto | 40 | 55 | 5 |
| General discovery | 20 | 30 | 5 |
| Total | 180 | 250 | 25 |

The family links were found in cached source pages from the previous validation batch. Filtered-search behavior and present listing availability have not been checked live in this step.

The collector alternates between searches, taking at most one detail attempt per active group on each pass. This gives interrupted runs a mix of groups. Family quotas count parser-complete rows only when extracted make and model match the requested family. Unexpected-family rows and incomplete rows remain in raw storage and logs. General discovery can overlap those families; a listing ID is collected once per run and assigned to one group.

This is a controlled convenience sample. Marketplace order and featured advertisements can affect selection. It does not guarantee balanced cities, years, variants, or prices. Those distributions will guide the next sampling decisions.

## PowerShell command

Run from the workspace:

```powershell
Set-Location "D:\Coding Projects\pakwheels-price-predictor"
$researchContact = Read-Host "Enter your collector contact email"
.\.venv\Scripts\python.exe scraper.py --sampling-plan configs/collection_pilot.json --output-dir data/raw/pilot_batch_001 --delay 5 --contact $researchContact
```

The target is 180 complete matches, not a guaranteed row count. Failed requests, unmatched identities, incomplete rows, or exhausted searches may leave a shortfall. Maximum detail attempts are 250 and maximum search attempts are 25 in one run. Every request waits five seconds before fetching. Reaching 180 listings alone requires at least 15 minutes of detail-request delay; response times and searches add time. Allow roughly 20-30 minutes, depending on the outcomes.

`--ads` now caps actual detail request attempts, including failures. Skipped saved rows and duplicate IDs do not consume it. For a shorter session, adding `--ads 50` caps that run at 50 detail attempts. The unchanged sampling plan can be resumed later with the same output directory. The default command uses the plan's full 250-attempt cap.

## What gets saved

All batch artifacts are under `data/raw/pilot_batch_001/`, which is ignored by Git:

| Artifact | Purpose |
|---|---|
| `pakwheels_raw.csv` | All parsed rows, including incomplete and unexpected-family observations |
| `pakwheels_clean.csv` | Parser-complete rows; training suitability is still pending |
| `manifest.json` | Sampling definition, cumulative counts, group assignments, dataset fingerprints, run references |
| `runs/<run_id>.json` | Request outcomes, elapsed time, code fingerprints, selections, failures, per-group limits and end reasons |
| `collection_summary.md` | Latest-run results and cumulative batch counts |
| `evidence/` | Cached HTML and hashes for source review; text previews for incomplete rows |
| `diagnostics/` | Search pages with no recognized listing links |

HTML is retained for the first 50 parser-complete observations in each run, all flagged parses, and an expected 10% hash sample after the initial review group. The run ID and listing ID determine that later sample, so it can be reproduced. Keep this evidence private because source HTML may contain seller information.

Each parsed row is saved immediately. CSV writes replace each file after writing a temporary file; raw and clean remain two separate files, not a database transaction. The next checkpoint rewrites both from the in-memory records. Manifests and run logs also use temporary-file replacement.

The manifest counts each stored URL once and reports unique listing IDs separately. It does not identify reposts under new IDs or prove the number of independent vehicles. Group assignments are sampling metadata, not prediction features.

## Resume and stopping

- Press Ctrl+C once to stop. The collector records `interrupted` and saves current rows and statistics. A second interruption or process kill can interrupt the final save.
- Run the same command later to resume. Complete saved IDs are skipped; incomplete rows can be retried. Family targets are cumulative within the batch. Search discovery starts at the configured first page again because marketplace ordering may change.
- Once every quota is fulfilled, the same command performs no additional requests. Use a new batch directory for a new sample.
- A different sampling definition is rejected for an existing batch directory. This prevents silently mixing collection configurations.
- HTTP 401/403/429 stops all collection and records `restricted`. Report that result before trying to continue; do not rerun around the restriction.
- Ordinary detail-request failures consume the budget and are logged without retries in that run. A failed search ends that group, while other groups can finish. Quota shortfalls produce status `partial`.

Do not add `--refresh` to the pilot command. Refresh is for deliberately replacing selected saved observations, not collecting a new independent sample.

## When the command finishes

Tell the agent to continue, and include the final console lines if the run stopped or failed. The agent will read the local manifest, summary, CSVs, and cached evidence. Next work is offline integrity checks, field missingness by family/year/city, identity review, and an initial quality report. Further collection commands will be handed to you when needed.

Offline verification before this handoff passed 25 behavioral tests with HTTP requests blocked. No live search or scraping run was performed for this step.
