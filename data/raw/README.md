# Raw collection files

- `baseline_2026-10-01/` preserves the initial two CSVs, original scraper, requirements, and environment/manifest evidence. Treat this snapshot as immutable.
- `current/` contains the active CSVs used by `scraper.py`. Completed listings still participate in the original resume behavior.

Both initial CSVs are source exports. The file named `pakwheels_clean.csv` is parser complete; it is not a normalized training dataset. Back up batches before larger collection. Private files here are excluded from Git; that is not a backup mechanism.
