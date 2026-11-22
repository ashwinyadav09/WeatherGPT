# Archive: Unverified artifacts

> [!CAUTION]
> **UNVERIFIED: generated from simulated data. Do not cite.**
>
> The files in this directory were produced by scripts that hard-coded or simulated the numbers they report. They do not represent real measurements from real experiments. They are archived here for traceability; they must not be referenced in pull requests, presentations or the project proposal.
>
> Archived on: 2026-11-22 as part of ticket R0.2 (REMEDIATION_PLAN.md §4).

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

## Replacement

Ticket R0.2 rewrites the scripts to produce `NOT MEASURED` when keys or a running stack are unavailable, and to record real measurements when they are. Run `python scripts/dev.py acceptance --strict` to see the current honest state.
