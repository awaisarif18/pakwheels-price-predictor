# Project workflow

Follow `docs/plans/DATA_MODELING_PILOT_PLAN.md` for implementation work. Production infrastructure follows the data/modeling pilot. Update `PROJECT_JOURNAL.md` after meaningful changes, distinguishing measured results from proposed work.

## Collection is run by the user

The user explicitly reserves execution of live scraping and collection commands.

1. Prepare code, configurations, and offline checks. Tests may use synthetic HTML or cached files with network calls mocked or blocked.
2. When live collection is needed, provide the exact PowerShell command and its output directory, then stop and wait for the user to report completion.
3. After the user reports completion and asks to continue, inspect the saved outputs and proceed with offline analysis.

Do not launch a live collector, refresh, `--fetch-missing`, or direct HTTP requests to PakWheels listing/search pages. A later request to continue does not authorize agent-run collection. Each needed live run is handed to the user.
