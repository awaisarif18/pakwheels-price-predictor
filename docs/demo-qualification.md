# Frozen predictor qualification and final test

Date: 21 October 2026. Candidate: `cars_demo_candidate_v1`. Outcome: saved research candidate; final demo gate failed.

## Implemented workflow

Implemented development-only support selection, a frozen candidate and error policy, native CatBoost training/saving, shared nine-input inference, documented save/load cases, one-time test evaluation, and a prediction-release gate. All work used saved files with HTTP blocked. No new collection, application server, or production deployment was run.

The selected model preserves the successful reduced CatBoost configuration: 300 iterations, depth 4, learning rate 0.05, RMSE loss, seed 42, CPU and one thread. It trains on all 449 development records. Fuel/body type and registration remain excluded; listing city remains included. Catalogue, input contract, support policy, model settings, development evidence, dependencies, code fingerprints, and examples accompany the native `model.cbm` file.

## Support and error criteria frozen before test

The [policy](../configs/demo_qualification_v1.json) defines conservative pilot defaults informed by development evidence. These are implementation choices for a local demo, not user-specified commercial tolerances, per-car guarantees, or estimates of market-wide reliability.

- A family needs at least 30 development groups. Each supported variant needs five independent eligible groups spanning all three development folds.
- Family/year combinations need five groups; family/city combinations need three. Each supported variant retains only observed eligible years, cities, mileage bounds, and transmission/displacement/assembly combinations. Unspecified and rare variants are refused.
- Every family needs at least 15 supported development groups. Final scoring needs 15 supported test rows overall and three per family.
- Overall MAE must be at most PKR 350,000. Family MAE caps are City 300,000, Civic 450,000, Alto 200,000, and Corolla 400,000.
- Overall and family median absolute percentage errors must be at most 10%, with no nonpositive predictions. Overall MAE must beat the comparable-price baseline by at least 10%; no family may be worse than its baseline.

The resulting scope contains 18 variants across all four families and covers 243/449 development rows. Their held-out development MAE is PKR 227,438, median percentage error 4.73%, and baseline improvement 24.8%. These are post-selection development results, not nested validation of the support-selection process. The qualification artifact was saved before fitting the final model and before test outcomes were opened.

### Frozen development scope

These entries describe the evaluated candidate, not a qualified prediction release. Each also has stored mileage and configuration bounds.

| Family | Variant | Observed supported years | Cities |
|---|---|---|---|
| Honda City | 1.3 i-VTEC | 2015, 2017, 2018, 2019, 2021 | Faisalabad, Islamabad, Lahore, Rawalpindi |
| Honda City | 1.3 i-VTEC Prosmatec | 2015, 2018, 2019, 2021 | Islamabad, Karachi, Lahore |
| Honda City | Aspire Prosmatec 1.5 i-VTEC | 2015, 2017, 2018, 2019, 2021 | Islamabad, Lahore |
| Honda Civic | Oriel | 2022, 2025 | Islamabad, Karachi, Lahore, Multan, Rawalpindi, Sargodha |
| Honda Civic | Oriel 1.8 i-VTEC CVT | 2017, 2018, 2020, 2021, 2022 | Islamabad, Karachi, Lahore, Multan, Rawalpindi, Sargodha |
| Honda Civic | RS | 2022, 2025 | Islamabad, Lahore, Multan, Sargodha |
| Honda Civic | VTi Oriel Prosmatec 1.8 i-VTEC | 2010, 2014, 2015 | Karachi, Lahore, Rawalpindi |
| Suzuki Alto | VX | 2010, 2011, 2012, 2022 | Faisalabad, Islamabad, Karachi, Lahore, Peshawar |
| Suzuki Alto | VXL AGS | 2019, 2020, 2021, 2022, 2024 | Islamabad, Karachi, Lahore, Rawalpindi |
| Suzuki Alto | VXR | 2010, 2011, 2012, 2019, 2020, 2021, 2022, 2024 | Faisalabad, Islamabad, Karachi, Lahore, Peshawar, Rawalpindi |
| Suzuki Alto | VXR (CNG) | 2010, 2011, 2012 | Karachi, Lahore, Rawalpindi |
| Suzuki Alto | VXR Upgraded | 2025, 2026 | Islamabad, Karachi, Lahore, Rawalpindi |
| Toyota Corolla | Altis Automatic 1.6 | 2013, 2015, 2017, 2018, 2019, 2020 | Islamabad, Karachi, Lahore, Rawalpindi |
| Toyota Corolla | Altis Grande CVT-i 1.8 | 2015, 2016, 2017, 2018, 2019 | Faisalabad, Islamabad, Karachi, Lahore, Multan, Peshawar |
| Toyota Corolla | Altis Grande X CVT-i 1.8 Black Interior | 2021, 2022, 2024 | Islamabad, Lahore, Multan |
| Toyota Corolla | GLi 1.3 VVTi | 2010, 2013, 2015, 2016, 2017, 2018, 2020 | Faisalabad, Islamabad, Karachi, Lahore, Multan, Rawalpindi |
| Toyota Corolla | GLi Automatic 1.3 VVTi | 2015, 2017, 2018, 2019, 2020 | Islamabad, Karachi, Lahore |
| Toyota Corolla | GLi Automatic 1.6 VVTi | 2013 | Islamabad, Karachi, Lahore |

## Reserved-test results

The saved model reproduced four documented cases in a fresh process. It was then evaluated once on the unchanged 114 reserved test records. The declared support rules accept 36/114, about 31.6%; the other 78 remain outside the demo scope. Full-population scores are an audit and do not expand supported scope.

| Test population | Rows | CatBoost MAE PKR | Baseline MAE PKR | Median percentage error |
|---|---:|---:|---:|---:|
| All reserved records | 114 | 257,246 | 433,877 | 5.39% |
| Inside frozen support bounds | 36 | 286,633 | 291,764 | 7.78% |

| Supported family | Rows | Candidate MAE PKR | Baseline MAE PKR | Median percentage error |
|---|---:|---:|---:|---:|
| Honda City | 3 | 198,183 | 213,333 | 3.30% |
| Honda Civic | 13 | 474,434 | 474,615 | 6.31% |
| Suzuki Alto | 15 | 159,980 | 156,733 | 11.21% |
| Toyota Corolla | 5 | 231,382 | 268,500 | 2.36% |

Four frozen checks fail:

1. Supported overall baseline improvement is 1.76%, below the required 10%.
2. Civic MAE is PKR 474,434, above its PKR 450,000 cap.
3. Alto median percentage error is 11.21%, above 10%.
4. Alto MAE is 2.07% worse than its baseline, rather than equal or better.

The all-114 MAE beats baseline by about 40.7%, but substituting it for the support-scope gate would change qualification after seeing test results. No limits, model settings, support boundaries, or family choices were changed. No alternative model was scored on this test after the failure. Small family counts limit the strength of conclusions.

The model remains a research candidate. General prediction serving is blocked; no interactive demo is released. Improving it using these findings requires a new independent holdout for the next final claim. The old test can no longer be described as unopened. Its original split files remain immutable historical snapshots; current usage is recorded separately in `data/manifests/test_usage/pilot_eval_f87fae24bb5634f0.json`.

## Artifacts and commands

- `reports/pilot/demo_qualification_v1/`: frozen support, limits, candidate, coverage decisions, catalogue, and development report.
- `models/pilot/cars_demo_v1/`: native model, nine-input contract, support, settings, versions, examples, and manifest.
- `reports/pilot/demo_test_v1/`: all 114 predictions, supported/unsupported reasons, baseline predictions, checks, and final metrics.

Thin offline commands are `scripts.qualify_demo`, `scripts.train_demo`, `scripts.evaluate_demo`, and `scripts.predict`. Existing outputs are refused. Test evaluation records a durable usage claim before opening outcomes, including interrupted scoring; subsequent evaluation or scope reselection on that opened split is refused. Do not rerun selection or change thresholds to pass this test.

Verify the saved model without opening test outcomes again:

```powershell
.\.venv\Scripts\python.exe -m scripts.predict --check-examples
```

This returns four verified examples. The prediction command is implemented but currently refuses service with the failed checks:

```powershell
.\.venv\Scripts\python.exe -m scripts.predict --input-json models/pilot/cars_demo_v1/example_input.json
```

Future training code uses the [shared adopted input contract](predictor-input-contract.md). The lower-level saved-candidate loader remains available for research and save/load checks; the public command requires a matching passed final evaluation before serving an estimate.

## Verification and next work

All 93 behavioral tests pass with HTTP blocked. Eleven new cases cover group-based target-independent support, invalid/extrapolated inputs, error-gate failures, development-only selection, native save/load and input parity, failed qualification and overwrites, tampering, one-time test usage including interrupted scoring, and release refusal for missing, failed, or mismatched final results.

Independent real-artifact checks confirm freeze/train/test chronology, unchanged nine-column semantics, all metrics recomputed from stored predictions, the baseline independently rebuilt from development data, exact test/development group isolation, registry hashes, and unchanged historical artifacts. No reserved-test prediction was used in training.

Next review and collect independent coverage for weak regions, particularly Civic and Alto, and create a genuinely new holdout before further selection. The user runs any live collection under AGENTS.md. A qualified interactive demo follows successful evaluation of a newly frozen candidate; production infrastructure remains deferred.
