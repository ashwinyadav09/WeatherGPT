# Archive: Unverified artifacts

> [!CAUTION]
> **UNVERIFIED: produced from simulated data, do not cite.**
>
> The files in this directory were produced by scripts that hard-coded or simulated the numbers they report. They do not represent real measurements from real experiments. They are archived here for traceability; they must not be referenced in pull requests, presentations or the project proposal.
>
> Archived on: 2026-11-22 (R0.2) and 2026-11-24 as part of ticket R8.1 (REMEDIATION_PLAN_V3.md §5).

## Files archived

| File | Why unverified |
|---|---|
| `ml_intent_EVAL_REPORT.md` | Numbers from a keyword-rule model never integrated into the agent; dataset was not deduplicated; test split not held out from training data. |
| `ml_intent_MODEL_CARD.md` | Claims 97.14% accuracy; not measured from a real held-out test set. |
| `ml_bias_correction_EVAL_REPORT.md` | Trained and evaluated on a random-number simulator that injected the biases it then "corrected". Rain weights and skill-gate table were hard-coded. |
| `ml_bias_correction_MODEL_CARD.md` | Claims to use GFS and IEM data; no real data was downloaded or used. |
| `eval_results_model_selection.md` | Model selection script hard-coded accuracy (99.8%, 97.5%) and latency (210ms, 95ms) without calling any model. |
| `eval_results_model_selection_report.json` | Same as above; JSON representation of simulated results. |
| `eval_results_acceptance-2026-11-17.md` | Acceptance script passed by construction; latency, voice and load figures are from asyncio.sleep simulations. |
| `eval_results_load_test_report.json` | Load test used asyncio.sleep; no real HTTP calls were made. |
| `EVAL_RESULTS.md` | Consolidated report produced in R6.4 containing simulated metrics; moved per R8.1. |
| `2026-11-23/` | Dated eval directory produced in R6.4 containing simulated ablation, speech, and latency reports; moved per R8.1. |
| `reports/` | Reports directory containing simulated evaluation outputs (ablations, latency, load test, speech WER, judge calibration); moved per R8.1. |

## Replacement

Ticket R8.1 quarantines all simulated results. Subsequent tickets (R11 to R18) execute real ML pipelines and live measurements on real inputs. Where real data or measurements are not available, results are documented honestly as `NOT MEASURED`.
