# WeatherGPT: Final Fix-and-Complete Prompt (R20)

Save as `.scratch/weathergpt/PROMPT_R20.md` and give it to Antigravity as the task. Date: 2026-11-25. Ticket ids are `R20.1` to `R20.15`. This prompt overrides any earlier status report, ledger entry or acceptance table.

---

## 0. Your mission

You are working on WeatherGPT, a multilingual weather and alerts assistant for India. A review of the repository on 2026-11-25 found that parts of the evaluation and documentation still contain **fabricated, constant or mocked numbers presented as measured results**, even though the rules in `.agents/rules/no-simulated-results.md` forbid it. Several ML models are real and good; others are incomplete.

Your job:

1. Remove every false or meaningless result (R20.1).
2. Make it mechanically impossible to produce such results again (R20.2).
3. Replace them with real measurements on real data (R20.3 to R20.13).
4. Rewrite the documentation from the measured results only (R20.14).
5. Audit your own work against the findings in section 1 (R20.15).

**Passing a gate is not your goal. A truthful measurement is your goal.** A failing result, a negative result and `NOT MEASURED` are all acceptable outcomes. A made-up number is never acceptable.

Read first: `AGENTS.md`, `.agents/rules/` (all), `REMEDIATION_PLAN_V3.md` (sections 2 and 3 apply in full), this file. Never open, print or commit `.env`. Keys come from environment variables (`GROQ_API_KEY`, `SARVAM_API_KEY`, `OPENROUTER_API_KEY`). If a key is missing, the dependent measurement is `NOT MEASURED`.

### Additional rules for this round (N1 to N8)

- **N1. No mocks outside unit tests.** Mock HTTP transports, stub adapters, canned LLM output and hand-built evidence packets may appear only in `services/api/tests/`. Evaluations, benchmarks, demos and reports must use real data or recorded real HTTP responses.
- **N2. No constants in results.** Every number in a result file must be computed from input files by code. No numeric literals as results, confidence bounds, "significant" flags, speedups, floors (`max(0.01, ...)`), defaults or fallbacks.
- **N3. No fallback values.** If a column, file or response is missing, raise an error or write `NOT MEASURED`. Never substitute a constant array or number.
- **N4. Provenance must be true.** `recorded_real_http` means the response was fetched from the real service by a script in this repository and stored with URL, time and sha256. `live_api` means fetched during this run. `human_labels` means a named human produced the labels (recorded in the ledger).
- **N5. `llm_path` must be true.** Any result that involves answer generation records `llm_path: live | disabled`. A run with `disabled` can never be reported as measuring the product's LLM path.
- **N6. No self-certification.** Never write "zero simulated", "all gates passed", "strictly adheres to Rules" or similar in docs, ledgers, PR descriptions or console output. Report values and let the audit judge.
- **N7. Evidence before claims.** Before marking a ticket done, run the proof commands and paste the real output path in the ledger. Do not claim anything you did not run.
- **N8. Stop rather than substitute (rule S1).** If real data, a key, or a human input is missing, write `BLOCKED.md`, mark the ticket blocked, and continue with the next ticket.

---

## 1. Verified findings (what must be fixed)

| ID | Finding | Ticket |
|---|---|---|
| V1 | `scripts/tasks/eval_ablations.py` is fabricated. Ablation 1 compares hard-coded arrays of ones and zeros. Ablation 2 falls back to a constant 0.705 when the CSV lacks `hybrid_hit_at_3` (the reported 70.5% with a zero-width interval is that fallback; the real hybrid recall@3 in `ml/rag/reports/metrics.json` is 0.8143) and sets the baseline to zeros. Ablation 3 reports the same predictions as "Ridge" and "LightGBM", sets raw, Ridge and LightGBM intervals to ±3–4% of the mean, floors a lower bound with `max(0.01, ...)` and hard-codes `significant: True`. Ablation 4 uses typed values (accuracy 0.85, LLM latency 55.0 ms, encoder latency 0.05 ms, speedup 1100) and `acc ± 0.03` intervals, and uses validation accuracy as if it were test accuracy. Ablation 5 uses typed values 1.0 and 0.84 with typed intervals. The report is labelled `recorded_real_http`. | R20.1, R20.11 |
| V2 | The guard test `services/api/tests/guards/test_no_synthetic_data.py` only flags literals assigned to metric-named variables and imports of `random`. It misses `np.random.default_rng(...)` (attribute use), `np.ones/np.zeros` constant arrays, numeric literals inside dict displays (`"mean": 0.85`), boolean literals such as `"significant": True`, and `max(0.01, ...)` floors. | R20.2 |
| V3 | `scripts/tasks/latency_report.py` and `load_test.py` run with `llm_path: disabled`, a mocked HTTP transport and the in-process app. The 41 ms p95 and load figures measure the template path with no LLM and no network, yet the acceptance table presents them as passing the product budgets. Each load level is a single burst of N requests. | R20.12 |
| V4 | The golden sets run on "per-city" fixtures (`eval/harness.py: get_per_city_forecast_transport`) whose values repeat across cities (34.2 °C for Mumbai, Ahmedabad, Surat, Nashik, Vadodara and Rajkot; 15.9 °C for Shimla, Chandigarh, Srinagar, Dehradun and Ludhiana; 0.0 mm rain everywhere). These are not recordings of the real service per city. The golden suites for non-English languages are template-built, so 100% pass rates are by construction. | R20.3, R20.12 |
| V5 | A lightning-safety question ("What safety rules should I follow during lightning and thunderstorms?") was answered "According to NDMA SACHET, weather information is available for What safety rules should I follow…?" and the case still passed. The question text was treated as a place name. Advisory answers are raw chunk dumps with chunk ids when the LLM is disabled. | R20.5 |
| V6 | RAG: `data/raw/knowledge/` holds 33 real downloaded PDFs plus `MANIFEST.json`, but the index (`seeds/knowledge/chunks.json`) still has 20 chunks, the same as the old hand-written markdown corpus. `seeds/knowledge/sources.csv` is still in the old format and lists `icar_agriculture_advisory.md` against the heatwave PDF URL. `ml/rag/download.py` uses `verify=False`. The 100 evaluation queries are labelled `human_labels` but no ledger entry shows H2 done by a human. `citation_precision` and no-RAG results are NOT MEASURED. | R20.10 |
| V7 | Bias correction (`ml/bias_correction/`): the "climatology" baseline MAE (1.1799) is identical to the multi-model-mean baseline, which indicates a bug. No persistence baseline, no per-lead or per-station results, no rain-skill confidence intervals. `artifacts/model_weights.json` looks like a single linear model, so the "LightGBM" label is unsupported. The data window ends 2024-10-31 although the archives extend to November 2026; two years of data are unused. | R20.6 |
| V8 | Intent (`ml/intent/`): real TF-IDF plus logistic regression on MASSIVE (4,842 rows, 5 languages). Validation macro-F1 0.63 and accuracy 0.79. The gold set is correctly NOT MEASURED (H1 blocked). Marathi and Odia have no training data; the card claims "subword transfer from Hindi/Bengali" which cannot work for Odia script. | R20.7 |
| V9 | Extreme events (`ml/extreme_event/`): real heatwave-only models. Stage 2 is not significantly better than the threshold rule (Brier difference interval −0.016 to +0.0012, p = 0.114; PR-AUC 0.6795 against 0.6934). The test block (May to October 2024) is effectively one heatwave season. Departures use ERA5 normals (`climatology_db.json`) against METAR observations. Stage 1 is not the long-history model planned. | R20.8 |
| V10 | Climate (`ml/climate/`): real ERA5, 8 grid cells, but event validation uses only 3 events and 3 controls. Isolation Forest is worse than the percentile baseline (recall 0.667 against 1.0; same false-flag rate 0.667). The control windows look hand-picked (a "non-event" Delhi window with 69.7 mm rain). | R20.9 |
| V11 | `docs/EVAL_RESULTS.md`, `docs/PROPOSAL_DELTAS.md`, `README.md`, `docs/ml-plan.md` and the progress ledger quote V1 and V3, state that all metrics are free of simulation, and list the five ablations as passed. | R20.1, R20.14 |
| V12 | Not yet reviewed and must be audited: the R17 web UI (ML Lab, trace panel, seven locales), the SACHET poller and the alert-freshness measurement, `scripts/tasks/demo.py`, translation seed validation. | R20.13 |

---

## 2. Tickets

Work in this order. One ticket = one branch = one PR. Run `python scripts/dev.py ci` and `python scripts/dev.py audit-results` before each PR. Do not edit guard tests, `CODEOWNERS` or `.agents/rules/` in the same PR as the code they check (G1), except R20.2 which exists to strengthen the guards and must be reviewed by Ashwin.

### R20.1 Remove the false results (do this first)

- Delete `scripts/tasks/eval_ablations.py`. Move `eval/results/ablations_report.json` and `reports/ablations_report.json` to `docs/archive/unverified/` with a banner "UNVERIFIED: contains hard-coded values".
- Move the current `eval/results/latency_report.json`, `load_test_report.json` and `reports/*latency*` to `docs/archive/unverified/` too. They are not product measurements (V3). They will be regenerated in R20.12.
- In `scripts/tasks/acceptance.py` and every doc, change the ablation, latency and load gates to `NOT MEASURED` until R20.11 and R20.12 produce audited results. Golden pass rates must be labelled "template-built cases over fixture data, not a product measurement" until R20.3 and R20.12.
- Remove from `docs/EVAL_RESULTS.md`, `docs/PROPOSAL_DELTAS.md`, `README.md` and `docs/ml-plan.md`: the ablation numbers, the 41 ms and load figures, the "100%" golden claims presented as product accuracy, and any claim of no simulation.
- Done when: a repository search for `70.5`, `1100x`, `0.84`, `zero simulated` and `strictly adheres` returns nothing outside `docs/archive/`; `python scripts/dev.py acceptance --strict` lists those gates as NOT MEASURED.

### R20.2 Make the guards actually work (red first)

Extend `services/api/tests/guards/test_no_synthetic_data.py` and `scripts/tasks/audit_results.py`. Write each new test first and show it failing on the current code. Preserve the old `eval_ablations.py` source as a string in the test file and assert the guard flags it.

For files under `ml/**`, `eval/**`, `scripts/tasks/**` (except the seeded bootstrap inside `ml/common/stats.py`):

1. Flag any attribute chain containing `random` (`np.random.*`, `numpy.random.*`, `random.*`, `default_rng`).
2. Flag `numpy.ones`, `zeros`, `full`, `ones_like`, `zeros_like` in `eval/**` and `scripts/tasks/**`.
3. Flag any non-integer float literal, except values listed in `services/api/tests/guards/float_allowlist.json` (each entry: file, value, reason; for example 0.05 for alpha, 2.5 and 97.5 for percentiles, 0.95 for confidence level). The allowlist is protected by CODEOWNERS.
4. Flag numeric or boolean literals used as values in dict displays whose key matches `mean|ci_lower|ci_upper|accuracy|latency|speedup|significant|passed|ok|f1|recall|precision|mrr|brier|wer|kappa|rate`.
5. Flag `max(<float literal>, x)` and `min(<float literal>, x)`.
6. Flag `.get(<key>, <numeric literal>)` and `x if cond else <numeric literal or constant array>` in result-producing code.

For `audit_results.py`, additionally:

7. Every ablation or comparison result must contain a per-case file (CSV) referenced in `inputs`, and `ml verify` or a sibling command recomputes means and bootstrap intervals from it within 1e-9.
8. Reject degenerate intervals (`ci_lower == ci_upper` with varying data) unless an explicit `degenerate_reason` field exists.
9. Reject results whose `provenance` is `recorded_real_http` or `live_api` but whose `llm_path` is `disabled` and which claim to measure answer quality or latency of the product.
10. Reject any result file that contains a key with `significant` unless the value is derived from the recorded interval (check in code: significant iff the interval excludes zero).
11. Add a docs scan: fail CI if `docs/**` or the ledger contains the phrases in rule N6.

Done when: the new tests fail on the old fabricated script and pass on clean code.

### R20.3 Record real data per city and replace the mock transport

- New script `scripts/tasks/record_fixtures.py`: for every city used in the golden sets (about 30), call the live Open-Meteo forecast and geocoding APIs and store the raw responses under `eval/recordings/open_meteo/<city>/<timestamp>.json` with a `MANIFEST.json` (URL, parameters, HTTP status, retrieved_at, bytes, sha256). Do not edit any recorded response. Record the live SACHET RSS feed the same way under `eval/recordings/sachet/`. If a call fails, exclude that city and list it.
- Replace `get_per_city_forecast_transport` with `RecordedHTTPTransport` that replays recordings by request hash and raises on a miss. Move any remaining mock transport to `services/api/tests/`.
- Rebuild the golden expectations by code: the script computes expected values (for example tomorrow's Tmax and rain sum) from the recording and writes the YAML. No number in a golden file may be typed by hand. Cases for all seven languages are generated from the same recordings.
- Done when: values differ per city and match the raw recordings; deleting a recording makes the test fail instead of passing silently; `audit-results` verifies recording hashes.

### R20.4 Live evaluation infrastructure

- `eval/llm_cache/`: a cache of real LLM and Sarvam calls keyed by sha256 of (provider, model, messages, parameters), storing response, latency, token counts, timestamp and `provenance: recorded_real_http`. `--live` forces fresh calls. Replays are allowed for reproducibility only and the result records `replayed: true`.
- `scripts/tasks/live_stack.py`: starts `docker compose up`, waits for `/healthz`, and returns the base URL. Results record `llm_path` (`live` or `disabled`) and `stack: docker_http | in_process`.
- Throttle to provider rate limits and record the throttle in the result. Watch Sarvam credits; use the cache and never repeat a call needlessly.
- Done when: a short live run with real keys stores cache entries and a result file that passes `audit-results`; without keys the run exits with NOT MEASURED.

### R20.5 Fix routing and answer bugs (tests first, all seven languages)

- Hazard-safety and advice questions (lightning, thunderstorm, heatwave, cold wave, flood, cyclone, crop protection) must route to the advisory path and never to place resolution. Add regression tests with the lightning question in all seven languages, and assert that no answer contains the question text as a place name.
- Confirm in code that the Orchestrator calls `IntentModel.predict` for routing, that `confidence` in the trace is the model's output (or `null`), that `models` lists only models that ran, and that `llm.provider` is the adapter that answered. Fix any deviation. Remove any remaining default place (for example Ludhiana) and default values such as `0.0 mm`.
- With the LLM enabled, advisory answers are composed from retrieved chunks with citations (chunk id, source, page from metadata only). With the LLM disabled, the fallback shows a quoted extract with its source and page, not a raw chunk dump with internal ids.
- Done when: the regression tests pass; the golden advisory cases check that the cited ids were retrieved.

### R20.6 Bias correction: complete it properly

- **Extend the data window.** The archives extend to November 2026. Probe each model's start date (record in the manifest). New split (record exact dates): train from the earliest common date to 2025-05-31, validation 2025-06-01 to 2025-10-31, embargo 7 days, test the most recent 12 complete months (about 2025-11-08 to 2026-10-31) so winter, summer heat and two monsoon-adjacent periods appear. Archive the old results as "prior split (2024 test block)". Do not tune on the new test block (S3).
- **Fix the baselines.** Compute: best single raw model, multi-model mean, persistence (previous day's observed Tmax), trailing 30-day mean-error correction, and station-day-of-year climatology from training years only. All must be real and distinct; a test asserts that the climatology and multi-model-mean numbers are computed by different code.
- **Train both models.** Ridge and LightGBM (`lightgbm` installed and used; if it cannot be installed, stop and write BLOCKED.md). Save both artifacts. Remove `model_weights.json` if it does not describe a real model.
- **Report** per lead day (1 to 3), per station, interval coverage, rain Brier, Brier skill score and Heidke skill score, each with paired weekly-block bootstrap 95% intervals against the best raw baseline. Enable correction per variable and per lead only where the interval excludes zero; store the gate in the artifact config and have `ForecastService` read it.
- **Rain truth.** Try CHIRPS point extraction from the cloud-optimised files for the stations (verify URL layout; record final or preliminary). If that fails, keep the ERA5-Land proxy and label it in `metrics.json` and the card.
- `predictions_test.csv` has one column per model and baseline; `ml verify bias_correction` recomputes every reported number.
- Done when: metrics include every baseline with distinct values, a card section lists limitations (METAR rounding, proxy rain truth, station coverage), and `ml verify` passes.

### R20.7 Intent and slots: complete it

- Translate the human-written seed queries into Marathi and Odia (and any missing Tier-1 language) with Sarvam (live calls, cached, labelled `machine_translated`). Validate that Odia strings contain Odia script. Add them to training. Remove the card statement about subword transfer.
- Error analysis: per-language and per-intent F1, confusion matrix, and a short written analysis of why macro-F1 is 0.63 (class imbalance, label mapping from MASSIVE, seed coverage). Improve data and features accordingly. Compare TF-IDF with frozen multilingual-e5-small embeddings plus logistic regression on the validation split; select by validation macro-F1.
- Calibrate with temperature scaling and choose τ on the validation split only.
- Run the live LLM function-calling comparison on the validation split now (label `validation_not_gold`) and on the gold set when H1 exists.
- Keep `enabled_in_production` only because routing falls back to the LLM below τ. The API, ML Lab and card show "validation metrics only; gold set NOT MEASURED" until H1 is supplied. `ml eval intent` computes gold metrics automatically when `eval/intent/gold_test_set.json` exists.
- Done when: the training data statistics list every language with its share of machine-generated rows.

### R20.8 Extreme-event models: complete it

- **Use the new split from R20.6** so that winter 2025–26 and summer 2026 are in the test block. Re-run the feasibility gate for heatwave, cold wave and heavy rain with the same thresholds (50 training and 20 test positive station-days). Report excluded hazards with counts.
- **Normals.** Probe IEM history per station. Use station-observation 1991–2020 normals where a station has at least 20 years with at least 80% valid days; otherwise use ERA5 normals and record `normals_source` per station and in the card.
- **Thresholds and calibration** are chosen on validation only (verify in code and add a test). Test is evaluated once.
- **Generalisation test.** Add leave-one-station-out evaluation (train without a station, test on it) and report per-station results.
- **Statistics.** Add weekly-block bootstrap intervals for PR-AUC, Brier skill score against climatology and recall at precision 0.5. State in the card and API when Stage 2 is not significantly different from the threshold rule. Only claim improvement over the rule if the interval excludes zero.
- **Stage 1 long history** (optional): if IEM station history allows, train Stage 1 on earlier years and test later; otherwise state the limitation.
- Done when: card, API and ML Lab show the real comparison against the rule, including a tie if that is the result.

### R20.9 Climate: complete it

- Research at least 15 documented extreme events (heavy rain, heatwave, cold wave, drought month) with citations (URL, date, place) in `ml/climate/events.csv`. Add at least 15 controls selected by a fixed deterministic rule written in the README (same cell, same calendar window, years where the seasonal total lies between the 25th and 75th percentile, excluding ±30 days around any listed event). No hand-picked controls.
- Evaluate at least 20 grid cells (all training stations plus major cities). Report event recall and false-flag rate with bootstrap intervals (flag small n), for Isolation Forest and the percentile baseline.
- If Isolation Forest does not beat the percentile baseline, set `isolation_forest_enabled=false`, serve the percentile baseline and say so in the card and ML Lab.
- Verify `modules/climate/service.py` contains no numeric constants; places not cached are fetched live from the Open-Meteo archive and cached; failures return an error, never constants. Add a test that searches the module for numeric literals.
- Add `ml verify climate` that recomputes trends and flags from the cached ERA5 files.

### R20.10 RAG: rebuild from the real documents

- Extract text from the 33 PDFs in `data/raw/knowledge/` (page by page, `pypdf`). For each document write extraction quality to `ml/rag/reports/extraction_report.json` (characters extracted, share in the expected script). Many Indic government PDFs use legacy fonts and extract as garbage: exclude such documents (`status: unusable_text`) or use OCR only if Tesseract is installed; never retype text.
- Chunk by page or heading (about 300 tokens, small overlap), with metadata (source, url, page, language, hazard, sha256). Write `seeds/knowledge/chunks.jsonl` from the script. Delete the seven hand-written markdown files and the old `chunks.json`.
- Regenerate `seeds/knowledge/sources.csv` from the downloader (new columns including `status`). Fix the mismatched ICAR row. In `ml/rag/download.py` verify TLS by default; for a host with a broken certificate chain add a documented per-host exception recorded in the manifest as `tls_verified: false`.
- Embeddings: `BAAI/bge-m3` or `intfloat/multilingual-e5-small`, with the model name and file hash recorded. Hybrid retrieval with BM25 and reciprocal rank fusion; threshold tuned on validation queries.
- **Evaluation queries must be human-written (H2).** Check the ledger and git history: if no human wrote `eval/rag/eval_queries.json`, rename it `eval/rag/agent_drafted_queries.json`, do not use it for reported metrics, and report retrieval metrics as NOT MEASURED. Provide `scripts/tasks/rag_label_tool.py` (prints chunks with ids) and `seeds/eval/rag_queries_template.json` so humans can label 100 queries.
- Add `citation_precision` (cited ids exist and were retrieved) computed from real answers.
- Done when: `n_chunks` reflects the real documents; every chunk's page and source come from extraction; answers cite chunk metadata only.

### R20.11 Real ablations (replace the deleted script)

Create `eval/ablations/` with one module per ablation and a runner `scripts/tasks/eval_ablations.py` that only orchestrates. Each ablation writes a per-case CSV, and results are computed with `ml.common.stats.paired_block_bootstrap` (or an equivalent resampling function in that module). No literals, no fallbacks.

1. **Tools versus no tools.** For at least 60 golden queries (English and Hindi), call the real LLM with no tools (question only) and the full system, against the R20.3 recordings. Metric: share of answers whose every number appears in the recorded evidence (the verifier), and absolute error against the recorded value. Live Groq calls, cached.
2. **Tools versus tools plus retrieval.** On human-written held-out queries: retrieval metrics for BM25, dense and hybrid; answer-level citation precision and judged support with and without retrieval. If H2 or H4 is missing, report only what is measurable and mark the rest NOT MEASURED.
3. **Raw NWP versus Ridge versus LightGBM versus baselines.** Directly from R20.6 predictions.
4. **Encoder versus LLM function calling.** Accuracy and measured latency of both on the same queries. Validation split now, labelled `validation_not_gold`; gold set when available.
5. **Cascaded versus native generation.** Take 100 evidence-grounded English answers; produce Hindi and Tamil versions with Sarvam translation (cascaded) and with native Groq generation; score numeric preservation with the verifier on normalised digits, and back-translation chrF with `sacrebleu`. Human ratings (H4) stay NOT MEASURED until supplied.

Done when: `ml verify`-style recomputation passes for every ablation file and all intervals have non-zero width unless the data are constant (with `degenerate_reason`).

### R20.12 Real latency, load and golden runs

- **Latency:** at least 100 queries across English, Hindi and the other Tier-1 languages through `/v1/chat` over HTTP on the Docker stack with the live LLM and live Sarvam, and recorded real forecasts. Record time to first token and total time (p50, p95), the `llm_path` of each query, the template-fallback rate and any errors. Report the numbers even if they miss the targets.
- **Load:** on the Docker stack, 20, 50 and 100 concurrent users, each level running for at least 60 seconds with a ramp, not a single burst. Run twice: (a) `llm_path: disabled` (labelled "API tier without LLM") and (b) live LLM at 5 concurrent users. Record errors, throughput and the machine specification.
- **Golden:** run all golden sets on the Orchestrator with the live LLM (cached responses allowed with `replayed: true`) and the R20.3 recordings. List every failing case. Do not edit a test to make it pass; fix the system or record the failure.
- Done when: results pass `audit-results` with `stack: docker_http` and truthful `llm_path`.

### R20.13 Audit the parts not yet reviewed

- **Alerts:** confirm the SACHET poller fetches the real feed (respect the 5-minute minimum interval, ETag, deduplication, verbatim relay). Provide `python scripts/dev.py alert-poller --hours 48` that logs `sent`, `first_seen_at` and `served_at` to `data/alerts/live_log.jsonl`, and a freshness script that reads that log. Alert freshness stays NOT MEASURED until a human has run the 48-hour poller (H8). Measure pipeline processing time separately from a real recorded fetch (R20.3).
- **Translations:** re-run the validation from R8.3 on all seven seed files and confirm no stub or English text sits where translations belong; confirm no `reviewed: true` was set by a script.
- **Web UI:** search `apps/web/` for mock data, hard-coded places, hard-coded metrics and a mock client used outside tests. The ML Lab and trace panel must show only values from `/v1/ml/*` and the `trace` event, and `NOT MEASURED` where data is missing. Confirm locale files exist for all seven Tier-1 languages and run the axe test in all seven. Write findings to `docs/AUDIT_UI.md`.
- **Demo:** `scripts/tasks/demo.py` must run against live services; if it uses recordings it must print `RECORDED` next to the data source.

### R20.14 Regenerate docs and acceptance from audited results

- Rewrite `scripts/tasks/acceptance.py`: each gate reads one audited result file and prints value, interval, provenance, `llm_path` and status `MEASURED_PASS`, `MEASURED_FAIL` or `NOT_MEASURED`. Failures are shown, never hidden. Targets are targets, not budgets that results are shaped to meet.
- Regenerate `docs/EVAL_RESULTS.md` and every `MODEL_CARD.md` from result files. Each card must include a "Limitations and negative results" section containing the facts from V7 to V10 that still apply.
- Rewrite `docs/PROPOSAL_DELTAS.md`: for each proposal objective give target, measured value with interval, or `NOT MEASURED` with the reason; list what changed (IMD and Bhashini keys pending and never used; Sarvam primary; voice optional; aviation not supported; extreme-event hazards excluded by the gate, if still true).
- Update `README.md`, `docs/architecture.md` and `docs/ml-plan.md` to match what exists.
- Add the N6 phrase scan to CI.

### R20.15 Self-audit and hand-off

- Write `docs/AUDIT_R20.md`: for each finding V1 to V12, the fix (commit, files) and the proof command with its actual output path. List all `NOT MEASURED` items, all blocked tickets, and all negative results.
- Run `python scripts/dev.py verify-results` and attach the output.
- Do not run your own "fresh-context audit" and report it as independent. Leave Appendix B of `REMEDIATION_PLAN_V3.md` for Ashwin to run in a separate session.
- Your final message must contain: what was fixed, what remains `NOT MEASURED` and why, what is blocked on humans, which models lost to their baselines, and which numbers worsened compared with the previous report. It must not contain the phrases banned in N6.

---

## 3. Human tasks (prepare templates and loaders only; never fill them in)

| ID | Task | Needed by |
|---|---|---|
| H1 | 350-query intent and slot gold set (50 per Tier-1 language), native or fluent speakers verify. File: `eval/intent/gold_test_set.json`. | R20.7, R20.11 |
| H2 | 100 retrieval queries with human-marked relevant chunk ids. Use `scripts/tasks/rag_label_tool.py`. | R20.10, R20.11 |
| H3 | 20 recorded utterances per language with reference transcripts in `eval/speech/`. Without them the speech WER gate stays NOT MEASURED. | speech eval |
| H4 | 30 answers scored by two human raters (judge calibration and translation ratings). | R20.11 |
| H7 | Native-speaker review of translated guidance. | R20.13 |
| H8 | Start the 48-hour alert poller and keep the machine running. | R20.13 |
| H9 | Run `python scripts/dev.py verify-results` and spot-check one number from each model against raw data by hand. | R20.15 |

---

## 4. Priorities and stop rules

Order: R20.1, R20.2, R20.3, R20.4, R20.5, then R20.6 to R20.10 (models; independent), then R20.11, R20.12, R20.13, R20.14, R20.15.

If time runs short, do not cut R20.1, R20.2, R20.3, R20.6, R20.10, R20.11 and R20.14; they remove false claims and carry the main results. Cut first: the optional Stage 1 long-history model (R20.8), CHIRPS extraction (R20.6, keep the labelled proxy) and the Marathi and Odia seed expansion beyond what Sarvam credits allow.

Stop rules: missing key, missing data, missing human input or an insufficient sample means `BLOCKED.md`, `NOT MEASURED` and moving on. Never substitute generated, mocked, defaulted or estimated values.

---

## 5. Definition of done (every ticket)

- Tests first and passing; `python scripts/dev.py ci` and `python scripts/dev.py audit-results` green.
- Every number reported by a script is computed from files listed in `inputs` with matching sha256, and `ml verify` or its equivalent recomputes it.
- The ledger lists the proof command and result path, and nothing the ticket did not actually do.
- No edit to guard files, `CODEOWNERS` or `.agents/rules/` in the same PR as guarded code (except R20.2, which needs Ashwin's review).
