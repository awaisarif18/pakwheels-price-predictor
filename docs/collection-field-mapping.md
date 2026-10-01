# Collection fields and validation results

Updated 1 October 2026. This implements the field decision in [the collection contract](../configs/collection_schema.json) during M0-to-M1 of [the active pilot plan](plans/DATA_MODELING_PILOT_PLAN.md).

## What the scraper now collects

The original thirteen columns remain. Schema version 2 adds these attributes and supporting metadata:

| Field | Accepted source | Meaning and missing-value rule |
|---|---|---|
| `make` | Current listing's JSON-LD `brand.name` | Source spelling with whitespace normalized; empty if no unique URL-matched product exists |
| `model` | Same product's `model` | Preserve names such as `iX` and `e-tron`; do not split the first words of an arbitrary title |
| `variant` | H1 after removing the verified make/model prefix and final model year | Preserve trim wording; leave empty if the heading disagrees with the structured family |
| `assembly` | Value next to `Assembly` in `#scroll_car_detail` | Reported value, not a verified manufacturing fact |
| `body_type` | Value next to `Body Type` in that table | Prefer the labeled value; URL-matched JSON-LD `bodyType` is a fallback |
| `registration_year` | Explicit registration statement in the current listing's seller comments | Optional integer; do not derive it from manufacture/model year, registration location, ownership transfer, or generic seller praise |
| `listing_date` | Explicit labeled date in the detail table | ISO date without an invented time; preserve the displayed text in provenance if parsing fails |
| `listing_date_type` | The date label | `updated` for the observed `Last Updated` label; recognize explicit posting labels separately |

The supporting columns are `identity_status`, `registration_year_meaning`, `registration_year_source`, `registration_year_status`, `field_provenance`, and `collection_schema_version`. The original `collected_at` remains a separate timestamp.

`field_provenance` contains compact JSON naming the extraction sources and retaining date text or explicit registration statements. It does not store the full seller description. Registration location, colour, and subjective condition claims are excluded from the CSV additions.

The extraction logic is in [collector/fields.py](../collector/fields.py). It accepts an already parsed document and returns fields without fetching or writing files. The existing scraper keeps fetching, pacing, core parsing, and exports. This separation lets us change optional field extraction without changing collection behavior or introducing an application framework.

## Source findings that changed implementation

### Structured data includes unrelated cars

One inspected page contained JSON-LD products for the advertised car and several recommendations. Selecting the first product, or combining fields across products, could silently assign another car's identity.

We accept a product only when its offer URL matches the requested listing's hostname and path. Query strings and trailing slashes do not affect that comparison. Multiple conflicting matching products leave structured fields unresolved. Synthetic tests cover both recommendation contamination and conflicting products.

### The date is an update date

Every inspected page labeled the date `Last Updated`. It must not be treated as the original publication date or vehicle age. The [Corolla example](https://www.pakwheels.com/used-cars/toyota-corolla-2013-for-sale-in-lahore-11998010) displayed `Oct 01, 2026` on the fetched page.

Use this date for freshness reporting initially. Chronological model evaluation should use dated collection batches and keep repeated vehicles together. An updated advertisement is not automatically a new independent observation. A true posting date remains unavailable in this sample.

### Registration year is sometimes factual text

Nine pages contained a standalone statement such as `Registered 2013` or `Registered: 2025`. These statements do not establish whether this means first registration in Pakistan, first registration abroad, or another registration event. All nine extracted years therefore have meaning `unknown`.

The parser also recognizes explicit first-registration jurisdiction statements. Those cases are covered by synthetic tests and were not observed in this live sample. Conflicting years remain empty with status `conflicting`. BMW iX had no accepted registration-year statement, so its value is empty.

Two sample records illustrate why registration year differs from model year:

| Vehicle | Model year | Stated registration year |
|---|---:|---:|
| Toyota Fortuner Legender | 2022 | 2023 |
| Toyota Raize Z | 2021 | 2025 |

These gaps do not prove lower usage or better condition. Retain the facts now and evaluate registration features later. A gap with unknown registration meaning must remain experimental.

### Assembly requires source-quality review

The two Audi e-tron pages reported different assembly values. [Listing 10946957](https://www.pakwheels.com/used-cars/audi-e-tron-2022-for-sale-in-islamabad-10946957) reported `Imported`; [listing 11950973](https://www.pakwheels.com/used-cars/audi-e-tron-2022-for-sale-in-karachi-11950973) reported `Local`. The scraper retains both source values.

This is a review candidate, not proof that either value is physically correct or incorrect. We should examine repeated model/assembly combinations in the broader pilot before deciding whether assembly needs filtering or catalogue checks. Do not overwrite source values using a brand-name assumption.

## Validation batch

Batch ID: `field_validation_2026-10-01`. Ten baseline URLs were fetched sequentially with a five-second delay. Four downloads were initial source inspection; the validation command fetched the six missing pages and reused those four files. No requests failed or triggered an access stop.

The enriched sample is separate from the baseline and active original CSVs. It contains updated observations of the same ten listings, not ten new independent vehicles.

| Result | Count |
|---|---:|
| Parsed and parser-complete | 10/10 |
| Make/model/variant extracted | 10/10 for each |
| Assembly extracted | 10/10 |
| Body type extracted | 10/10 |
| Listing date extracted | 10/10, all labeled updated |
| Registration year extracted | 9/10, all with unknown meaning |
| Registration year unavailable | 1/10 |

The labeled fields and explicit registration statements were inspected across the ten cached pages. These counts measure availability in this sample. They do not estimate availability or source correctness across the marketplace.

Private artifacts:

- [Enriched raw CSV](../data/raw/field_validation_2026-10-01/pakwheels_raw.csv)
- [Batch manifest](../data/raw/field_validation_2026-10-01/manifest.json), including HTML checksums and per-run request records
- [Validation summary](../data/raw/field_validation_2026-10-01/validation_report.md)
- [CSV integrity audit](../reports/pilot/field_validation_2026-10-01/initial_audit.md)

The baseline raw and clean files and both original active CSVs still have SHA-256 `1016b4169ffeeb21837a424317522eea1c8679a32c3d9b42c07c929b67c03aed`. They were not rewritten. The original identity review worksheet was also preserved.

## Reproduce or continue

Offline reparse using saved evidence:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_collection
```

Fetch missing evidence only when needed:

```powershell
.\.venv\Scripts\python.exe -m scripts.validate_collection --fetch-missing --delay 5
```

Collect into a new directory with the extended scraper:

```powershell
.\.venv\Scripts\python.exe scraper.py --pages 1 --ads 10 --start-page 1 --delay 5 --output-dir data/raw/pilot_batch_001 --contact "your-real-email@example.com"
```

Use `--refresh` to re-fetch selected complete rows in the chosen directory. Existing rows are skipped by default. Old-schema rows retain empty new fields until refreshed; merely exporting them must not invent provenance or a schema version.

`--ads` still caps selected URLs, including skipped saved rows. The validation command records requests and evidence; the general scraper does not yet produce a full run manifest. Add family sampling and general batch accounting before the varied 100-300-record collection pilot. Review canonical identity names and assembly reliability during that pilot.

Verification includes fifteen behavioral tests and the two existing parser self-tests. No training or model-performance result exists yet.
