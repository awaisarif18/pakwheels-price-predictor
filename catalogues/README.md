# Vehicle catalogues

`cars.json` contains four candidate families: Toyota Corolla, Honda City, Honda Civic, and Suzuki Alto. Its 57 variant labels preserve observed source wording with case/whitespace normalization. These are identity labels for preparation, not a complete market catalogue or a declaration of supported prediction inputs.

`pilot/identity.py` matches explicit catalogue labels. It does not merge similar-looking trims or use fuzzy matching. Unknown variants stay unresolved; an unspecified variant does not mean base trim. Extend aliases only with documented source evidence and protect meaningful engine, transmission, trim, and package distinctions.

See [the first pilot review](../docs/pilot-data-review.md). The original pending worksheet remains available at `reports/pilot/identity_review.csv`; its existence does not mean every identity was manually certified. No motorcycle catalogue exists yet.
