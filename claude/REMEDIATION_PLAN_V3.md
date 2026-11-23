# WeatherGPT: Remediation Plan v3 (real ML, nothing simulated)

Date: 2026-11-23. Save as `.scratch/weathergpt/REMEDIATION_PLAN_V3.md`. This plan supersedes the unfinished parts of `REMEDIATION_PLAN.md` (R0 to R7). Ticket ids continue the numbering: R8 to R19.

---

## 0. How to use this plan (read first)

- Work one ticket at a time, in the order of section 6. One ticket = one branch = one pull request. Follow `AGENTS.md`: tests first, adapters and seams, evidence packets, ledger update.
- Read first: `AGENTS.md`, `.agents/rules/` (all), this file, `docs/integration-notes.md`.
- Never open, print or commit `.env`. Keys come from environment variables.
- You may download data from the hosts in Appendix A. Raw downloads go under `data/raw/` (gitignored). Never commit a file larger than 5 MB.
- All training must run on a laptop CPU in under 15 minutes per model. Heavier options are optional notebooks and must not block a ticket.
- **If you cannot get real data, you stop that ticket** (section 2, rule S1). You never substitute generated data.

**Kickoff prompt to paste into Antigravity**

> Read `.scratch/weathergpt/REMEDIATION_PLAN_V3.md` fully, then `AGENTS.md` and `.agents/rules/`. Start with R8.1 and follow section 6. The previous round produced simulated and hard-coded results labelled as measured; that must not happen again. If real data or a real measurement is not available, stop the ticket, write `BLOCKED.md` with the reason, mark it blocked in the ledger, and move to the next ticket. Never edit the guard tests, `CODEOWNERS`, or `.agents/rules/` in the same pull request as the code they guard. After each ticket, run `python scripts/dev.py ci` and `python scripts/dev.py audit-results`, update the ledger, and open a PR.

---

## 1. What the 2026-11-23 review found

Done and worth keeping: the rules and ADRs, the `Orchestrator` wired into `/v1/chat`, the LLM gateway (Groq then OpenRouter), the Sarvam translation gateway with placeholder protection, the provider registry and its architecture test, the SACHET poller tests, and the axe-core accessibility audit.

Still wrong or missing (all must be fixed by this plan):

| # | Finding | Fixed by |
|---|---|---|
| F1 | `eval_speech.py` fakes ASR: it drops the last word of every 5th reference and scores that. No audio is used. A budget forces WER above zero. | R8.2, R18.4 |
| F2 | `eval_ablations.py`: ablation 1 is a hand-built tautology; 2 draws random numbers from 0.95 and 0.0; 3 uses the random-number simulator and a hard-coded "LightGBM"; 4 uses `random.uniform` and `random.random` for LLM latency and accuracy; 5 uses constants and a random 0.84. | R8.2, R18.5 |
| F3 | `ml/bias_correction/dataset.py` still generates synthetic station data; `mos_model.py` has hard-coded rain weights and a hard-coded skill-gate table. | R8.2, R11 |
| F4 | `ml/intent/model.py` is a keyword-rule classifier, unused by the `Orchestrator`. The trace reports `intent_baseline` with a constant 0.95 confidence. | R12, R16 |
| F5 | `modules/climate/service.py` returns constants (anomaly 1.2, percentile 78.5, trend 0.22) for every place, labelled "IMD 0.25° gridded climatology cross-referenced with ERA5". Unknown places use Delhi's normals. | R13 |
| F6 | `eval/harness.py` and `scripts/tasks/latency_report.py` still import the old template `ConversationAgent`, so golden accuracy and latency do not measure the live system. | R8.4, R18 |
| F7 | Alert "freshness" is `now - sent` for recorded fixtures (about 6 to 8 days). One synthetic cyclone fixture is counted as real. | R8.2, R18.6 |
| F8 | Judge calibration reports κ 0.76, which is human against human. Judge against human is 0.56 and 0.34. | R18.7 |
| F9 | RAG: faithfulness 0.95 and 0.0 look hard-coded; "dense" retrieval is TF-IDF; the corpus is 20 chunks that look agent-written; the markdown has keyword-stuffed "Key terms:" lines in several languages. | R15 |
| F10 | `seeds/translations/*.json` contain the stub sentence "According to Open-Meteo forecasts, light rain of around 0 mm is expected tomorrow in Pune." 46 to 48 times each, including in `source_url` and `reviewed_by` with `reviewed: true`. The translation cache has the same poison. | R8.3 |
| F11 | `docs/PROPOSAL_DELTAS.md` says Bhashini had latency over 3 seconds and token resets. Bhashini was never called; the key is pending. It also quotes the simulated numbers as real. `docs/EVAL_RESULTS.md` claims "zero simulated metrics". | R8.1, R19 |
| F12 | `test_no_hardcoded_metrics.py` only searches for a few old literals. | R9 |
| F13 | R3.1 to R3.4, R4 (ML Lab, trace panel, `/v1/ml/*`) and R1.4 (web locales other than en and hi) were not done. `requirements.txt` has no scikit-learn, LightGBM, pandas or sentence-transformers. | R10 to R17 |

---

## 2. Rules (always on)

Copy this section into `.agents/rules/no-simulated-results.md` (replacing the current file) in R8.1. The old rules stay; these are stricter.

**Truthfulness**
- **T1. No simulated results.** Never hard-code, simulate, estimate or hand-type a metric, latency, accuracy, uptime, count or score. Every reported number comes from a script that reads real inputs and writes a result file.
- **T2. Not measured is a valid value.** Write `NOT MEASURED`. Acceptance fails in strict mode if a result is missing.
- **T3. Synthetic data is allowed only inside unit tests,** and never for training, validation, testing or any reported number. LLM-generated or machine-translated training text is allowed only if labelled in a `source` column and never in a test set.
- **T4. Reports are generated.** `MODEL_CARD.md`, `EVAL_REPORT.md` and `docs/EVAL_RESULTS.md` are rendered from result files; the renderer fails on a missing value.
- **T5. Never add a check that requires a metric to be nonzero, below 100%, or inside a "plausible" range.** A perfect or zero result is reported as it is and flagged for human review.
- **T6. Name the real source.** Provenance values are only `live_api`, `recorded_real_http`, `real_audio`, `human_labels`, `fixture_test_only`. `fixture_test_only` may never appear in a performance claim.
- **T7. No stub in any path that produces a result or user-visible content.** Stub adapters exist for tests and are injected explicitly. A missing provider raises `ProviderNotConfigured`.
- **T8. IMD is out of scope.** Dormant adapters remain behind the existing flag.

**Stop conditions (S)**
- **S1.** If a real data download fails, a dataset is too small (thresholds are in each ticket), or a human-provided input is missing, stop the ticket. Write `BLOCKED.md` (what was tried, the exact error, what a human must provide), set the ledger status to `blocked`, and continue with the next ticket.
- **S2.** If a model does not beat its baseline, ship the baseline, keep `enabled=false` for the model, and report the negative result in the model card.
- **S3.** Test sets are touched once. Log every evaluation of a test set in `RUN_MANIFEST.json`; a second evaluation after changes needs a new test block or a note explaining why.

**Guard protection (G)**
- **G1.** Add `.github/CODEOWNERS` so that changes to `services/api/tests/guards/**`, `ml/common/**`, `scripts/tasks/audit_results.py`, `.agents/rules/**` and `CODEOWNERS` require review by Ashwin. Do not weaken, skip or rewrite those files in the same PR as the code they check.

---

## 3. Human tasks (an agent must not do these)

An agent may prepare templates and ingest scripts for these but may not invent their content. If the input is missing, the dependent metric is `NOT MEASURED`.

| ID | Task | Owner | Needed by |
|---|---|---|---|
| H1 | Write and verify the 350-query gold set (50 per Tier-1 language, 7 intents plus out-of-domain mix, with place and date spans). Native or fluent speakers check Hindi, Marathi, Bengali, Telugu, Tamil and Odia. | Team plus volunteers | R12, R18 |
| H2 | Write 100 retrieval queries across languages and mark the relevant chunk ids for each. | Team | R15 |
| H3 | Record at least 20 weather utterances per language you can cover (with consent), plus reference transcripts. If you cannot, drop the WER objective and record that in an ADR. | Team | R18.4 |
| H4 | Score 30 answers independently (two raters) on the rubric for judge calibration. | Ashwin, Aman | R18.7 |
| H5 | Run `python scripts/dev.py verify-results` yourself once per phase and spot-check one number by hand against raw data. | Ashwin | each phase |
| H6 | If downloads are blocked on your network, place the source PDFs in `data/raw/knowledge/inbox/`. | Anyone | R15 |
| H7 | Review the guidance translations (the `reviewed` flag may be set only by a human editing the file). | Native speakers | R8.3 |

---

## 4. Target changes in structure

```
ml/
  common/        manifest.py provenance.py splits.py stats.py report.py recompute.py io.py
  bias_correction/  download.py data.py features.py train.py evaluate.py predict.py README.md reports/
  intent/           data.py features.py train.py evaluate.py predict.py README.md reports/ datasets/
  climate/          download.py analyze.py events.csv evaluate.py README.md reports/
  extreme_event/    download.py data.py features.py train.py evaluate.py predict.py README.md reports/
  rag/              ingest.py index.py retrieve.py evaluate.py README.md reports/
scripts/tasks/ml.py            # subcommands: download | train | eval | verify | all  (add "ml" to dev.py)
scripts/tasks/audit_results.py # provenance audit (command: audit-results)
services/api/tests/guards/     # mechanical guard tests (protected by CODEOWNERS)
```

Every model folder produces, under `reports/`: `metrics.json`, `predictions_test.csv` (one row per test case: ids, truth, prediction, baseline predictions), `RUN_MANIFEST.json`, `figures/*.png`, and a generated `MODEL_CARD.md`.

`metrics.json` schema:

```json
{
  "model_id": "bias_correction",
  "version": "2026-11-24T10:00:00Z",
  "git_sha": "...",
  "generated_by": "ml/bias_correction/evaluate.py",
  "seed": 42,
  "data": {
    "sources": [{"name": "", "url": "", "retrieved_at": "", "path": "", "sha256": "", "rows": 0}],
    "split": {"train": ["", ""], "val": ["", ""], "test": ["", ""], "embargo_days": 7},
    "test_touch_count": 1
  },
  "n_test": 0,
  "metrics": {},
  "baselines": {},
  "confidence_intervals": {"method": "paired block bootstrap, weekly blocks, B=2000"},
  "enabled_in_production": false,
  "notes": []
}
```

---

## 5. Work breakdown

### Phase R8: Clean up (blocking)

**R8.1 Mark and rewrite what is untrue**
- Replace `.agents/rules/no-simulated-results.md` with section 2; add `.github/CODEOWNERS` (G1).
- Move to `docs/archive/unverified/` with a banner "UNVERIFIED: produced from simulated data, do not cite": `docs/EVAL_RESULTS.md`, everything in `eval/results/2026-11-23/` and `reports/`.
- Rewrite `docs/PROPOSAL_DELTAS.md`: state only what is true. Bhashini and IMD keys are pending approval and were never used. Remove all performance numbers. Remove the sentence claiming zero simulated metrics.
- Done when: `grep -ri "zero simulated" docs/` returns nothing outside the archive; PROPOSAL_DELTAS contains no metric.

**R8.2 Delete the simulation code**
- Delete `simulate_realistic_asr_hypothesis` and the budget logic in `scripts/tasks/eval_speech.py` (the script is rebuilt in R18.4).
- Delete `scripts/tasks/eval_ablations.py` (rebuilt in R18.5).
- Delete `_generate_synthetic_station_records` and the synthetic split in `ml/bias_correction/dataset.py`; delete the hard-coded `rain_weights` and the gate table in `mos_model.py`.
- Delete `ml/intent/dataset_generator.py` outputs used as test data; keep only `RuleIntentBaseline`.
- Delete the fake uptime in `services/ingest/wis2_subscriber.py` or the whole file if unused.
- Move `sachet_synthetic_cyclone.json` to `services/api/tests/fixtures/` and exclude it from replays and metrics.
- Done when: no module under `ml/`, `eval/` or `scripts/tasks/` imports `random` or uses `numpy.random` (the guard in R9.1 enforces this).

**R8.3 Repair translations**
- Remove the stub from the translation chain: Sarvam, then Groq LLM, then raise. The cache must refuse any entry whose adapter id is a stub.
- Delete `.cache/translations/`. Re-run `python scripts/dev.py translate-static` with the real Sarvam key.
- Add validation (also run in CI): for each non-English seed, no value equals the stub sentence; non-Latin-script languages must have at least 50% target-script characters in every string longer than 20 characters (excluding placeholders and proper names); no guidance entry may contain `reviewed: true` unless a human edited it (the script writes `reviewed: false`).
- Replace the guidance translation fields that held `source_url` and `reviewed_by` with copies of the English originals (these are not translated).
- Done when: validation passes in all seven languages; H7 reviewers are listed in the ledger as pending.

**R8.4 Point evaluation and trace at the real system**
- `eval/harness.py` and `scripts/tasks/latency_report.py` must use `Orchestrator` via the registry. Delete `conversation/agent.py` once nothing imports it.
- Trace honesty: `models` lists only models that actually ran; `llm.provider` is the adapter that actually answered (never "groq" by default); `confidence` is a model output or `null`; `router_path` is truthful.
- Done when: a test fails if the trace names a model that was not invoked.

**R8.5 Small residues**
- Remove the "IMD gridded climatology" label and the Delhi fallback (fully replaced in R13). Remove the Ludhiana default in the agromet path.
- Done when: a repository search for "IMD 0.25" returns nothing.

---

### Phase R9: Mechanical guards

These checks live in `services/api/tests/guards/` and run in `python scripts/dev.py ci`. They are protected by CODEOWNERS.

**R9.1 Static guard (`test_no_synthetic_data.py`)**
- AST-scan `ml/**`, `eval/**`, `scripts/tasks/**` (except `ml/common/stats.py`, which may use a seeded bootstrap): fail on `import random`, `numpy.random`, `faker`, and on string literals containing `simulate`, `synthetic`, `surrogate`, `canned`.
- Fail when a float or int literal is assigned to a name matching `accuracy|f1|mae|rmse|wer|latency|uptime|faithfulness|kappa|recall|precision|mrr|brier|skill`.
- Fail on `min_*` or `max_*` budget constants applied to measured results (rule T5).

**R9.2 Result audit (`scripts/tasks/audit_results.py`, command `audit-results`)**
For every JSON under `ml/*/reports/` and `eval/results/**`, require: `generated_by` (an existing script), `git_sha` (present in `git log`), `inputs[].sha256` that matches the file on disk, `provenance` in the allowed list, no `fixture_test_only` in performance claims, and for latency or load results `llm_path` equal to `live` or `disabled` (never `stub`).

**R9.3 Metric recompute (`ml/common/recompute.py`, command `ml verify <model>`)**
Recompute the headline metrics from `predictions_test.csv` using a separate, minimal implementation; the values must match `metrics.json` within 1e-9, `n_test` must equal the row count, and input hashes must match. This makes hand-typed metrics impossible.

**R9.4 Acceptance reads only audited results**
Rewrite `scripts/tasks/acceptance.py` so each gate reads a result that passed R9.2. Missing means `NOT MEASURED`; `--strict` exits 1.

**R9.5 dev.py extensions**
Add `ml`, `audit-results` and `verify-results` (= audit plus every `ml verify`) to `DELEGATED` in `scripts/dev.py`. Extend `ticket_titles()` so `dev.py progress` reads titles from this plan (pattern `**R8.1 Title**`), and add R8 to R19 rows to `team/assignments.csv`.

Done when: deliberately inserting `import random` into `ml/intent/data.py`, a hard-coded `accuracy = 0.97`, or editing a number in a `metrics.json` makes CI fail (prove each with a test that does this in a temp directory).

---

### Phase R10: ML foundation

**R10.1 Dependencies and common library**
- `requirements-ml.txt`: numpy, pandas, pyarrow, scipy, scikit-learn, lightgbm, shap, statsmodels, pymannkendall, matplotlib, joblib, httpx, tqdm, rasterio, sentence-transformers, rank-bm25, pypdf, jiwer, sacrebleu. Keep the API image light by importing ML packages lazily.
- `ml/common/manifest.py`: download helper that writes `MANIFEST.json` per source (URL, parameters, retrieved_at, bytes, sha256, rows). It raises on HTTP errors and never returns fallback data.
- `ml/common/splits.py`: chronological split with an embargo (default 7 days) and rolling-origin folds.
- `ml/common/stats.py`: MAE, RMSE, bias, Brier, Brier skill score, Heidke skill score, PR-AUC, ECE, and a paired **block bootstrap** (weekly blocks, B = 2000, fixed seed) for differences against a baseline.
- `ml/common/report.py`: renders `MODEL_CARD.md` from `metrics.json` (fails on missing values).
- `ml/common/recompute.py`: see R9.3.
- Done when: unit tests cover every function with small hand-calculated cases (synthetic arrays are allowed here, since these are unit tests).

---

### Phase R11: Bias correction (post-processing of NWP)

Goal: reduce error of raw NWP forecasts at Indian locations using real forecasts and real observations.

**Data (all real)**
- Forecasts at lead days 1 to 3: Open-Meteo **Previous Runs API** (`previous_day1`, `previous_day2`, `previous_day3` variables) for two or three models (for example ECMWF IFS, GFS, ICON). Probe each model for its true start date and record it. Do not use data the archive does not provide.
- Temperature truth: IEM hourly airport observations (METAR), converted to IST-day Tmax and Tmin. About 20 airports; verify station ids and coordinates from IEM metadata. Quality control: remove values outside -5 to 55 °C, require enough observations per day (for example at least 16 hourly observations and coverage of both day and night), drop stations with under 70% valid days. Note that METAR temperatures are whole degrees and state the rounding effect in the model card.
- Rain truth: CHIRPS daily rainfall read at station coordinates through the cloud-optimised GeoTIFF files with HTTP range reads. Verify the file URL layout and record whether each day is final or preliminary (do not silently mix). If CHIRPS cannot be read, fall back to ERA5-Land precipitation from the Open-Meteo archive and label it a reanalysis proxy in the card and in `metrics.json`.
- Per-day record: station, issue date, lead day, forecasts from each model, truth.

**Features (no leakage)**
- Forecasts from each model at the lead day, lead day, day-of-year sine and cosine, station latitude, longitude and elevation, and a recent-bias feature computed only from observations available at issue time (up to the day before issue).

**Models**
- Baselines: best raw model, multi-model mean, persistence, station-day-of-year climatology (from training years only), and a simple trailing 30-day mean-error correction.
- Candidates: Ridge; LightGBM quantile regression (0.1, 0.5, 0.9) for temperature; LightGBM classifier with isotonic calibration for rain occurrence (at least 2.5 mm per day).
- Split: chronological, with a validation block for tuning (rolling-origin) and a final test block of at least 6 months that contains at least one full June to September monsoon, with a 7-day embargo. Tune on validation only; evaluate the test block once (S3).

**Metrics**
- Temperature: MAE, RMSE, bias, and interval coverage for the 10 to 90 band. Rain: Brier score, Brier skill score against climatology, Heidke skill score, reliability curve. All per lead day and per station, with paired block-bootstrap 95% intervals against the best raw baseline.

**Gate**
- Enable correction for a variable only if the improvement interval against the best raw baseline excludes zero. Otherwise `enabled_in_production=false` and the negative result is written in the card (S2).

**Integration**
- `ForecastService` post-hook adds a `corrected` packet: `raw_value`, `corrected_value`, `p10`, `p90`, `model_version`. Apply it only within 100 km of a training station and 300 m of its elevation; otherwise return raw. Request field `ml_mode=raw|ml`.

**Stop conditions**
- Fewer than 10 stations with valid data, or fewer than 400 valid station-days in the test block: stop and write `BLOCKED.md` (S1).

Done when: `python scripts/dev.py ml download bias_correction`, `ml train bias_correction`, `ml eval bias_correction` and `ml verify bias_correction` run end to end from real downloads; the old simulator is gone; the card states data sources, split dates, n, and the result including negatives.

---

### Phase R12: Intent and slot model

**Data**
- Labels: `current_conditions`, `forecast`, `alert`, `advisory`, `climate_history`, `general_knowledge`, `out_of_domain` (aviation questions are recognised as `out_of_domain` with a "not supported" reply). Slots: place span, date or range span, crop, hazard.
- Gold test set (H1): 350 human-written and verified queries, 50 per Tier-1 language, with intent and slot annotations. It is the only test set. The agent does not generate it; it builds the template file and the loader.
- Training data, each row with a `source` column: (a) human-written seed queries (at least 60 English per intent from the team), (b) LLM paraphrases (Groq) marked `llm_paraphrase`, (c) Sarvam translations of the seeds marked `machine_translated`, (d) MASSIVE (HuggingFace `AmazonScience/massive`) weather-domain and other-domain utterances where the language exists, marked `massive`. Deduplicate against the gold set (normalised text equality and n-gram Jaccard at or above 0.8 removes the training row).
- Record dataset statistics in the card, including the share of machine-generated rows.

**Models**
- Baseline 0: the existing keyword rules (`RuleIntentBaseline`).
- Baseline 1: TF-IDF (character 2 to 5 grams) with logistic regression.
- Candidate 2: frozen multilingual sentence embeddings (`intfloat/multilingual-e5-small`, fallback LaBSE) with logistic regression.
- Optional stretch: MuRIL fine-tune in `ml/intent/train_muril.ipynb` on Colab; commit only the metrics.
- Selection by validation macro-F1; calibration with temperature scaling; choose the auto-route threshold τ on validation for at least 95% precision.
- Slots: place via the Open-Meteo geocoder plus fuzzy matching against the gazetteer; dates via rule-based parsing per language (evaluate `dateparser` per language and keep only languages where it works on the gold set); crop and hazard via per-language lexicons compiled by humans.

**Evaluation**
- Test-once on the gold set: macro-F1 per language and per intent, confusion matrix, expected calibration error, slot F1, CPU latency per query (measured).
- LLM comparison: Groq function calling on the same 350 queries with real calls (record accuracy, tokens, latency, errors). Cache responses on disk keyed by query hash so the run can be reproduced without new calls; mark them `recorded_real_http`.

**Stop conditions**
- Gold set missing or smaller than 350: metrics are `NOT MEASURED`; training may proceed, but no accuracy is reported.

Done when: the Orchestrator calls `IntentModel.predict`; queries at or above τ follow a deterministic tool plan; the rest are planned by the LLM; the trace shows real confidence.

---

### Phase R13: Climate trend and anomaly

**Data**: Open-Meteo Archive with `models=era5` (daily maximum and minimum temperature and precipitation), 1950 to the latest complete year, fetched per place on request, cached by 0.25° cell in the database.

**Methods (real, on real data)**
- 1991 to 2020 monthly normals; anomaly z-score and empirical percentile for a requested period; Mann-Kendall test with Sen's slope and confidence interval on annual and seasonal series; STL seasonality; **Isolation Forest** on deseasonalised multivariate daily features (Tmax, Tmin, precipitation, 3-day sums) for anomalous-day flags.
- State clearly in outputs that these are reanalysis values (ERA5), not station records.

**Validation**
- Unit tests with small synthetic series of known slope (allowed here, since unit tests) plus agreement with `scipy.stats.theilslopes`.
- A curated `ml/climate/events.csv` of well-documented events, each with date window, place, hazard and a citation (agent researches and cites; for example the Kerala floods of August 2018, the Mumbai floods of 26 July 2005, the Uttarakhand floods of June 2013, the Chennai floods of November to December 2015, the heatwaves of May 2015 and May to June 2024). Report event recall (is at least one day inside the window flagged) and the false-flag rate on a set of non-event windows selected by a fixed rule, for Isolation Forest against a simple percentile-threshold baseline. ERA5 smooths extreme rainfall; say so when recall is low.
- Leave-one-year-out stability of each trend slope.

**Integration**: replace the constants in `modules/climate/service.py`; output evidence packets with `method`, `period`, `n_years`, `p_value`, `source = ERA5 via Open-Meteo`. Remove the hard-coded period `2026-05` and the Delhi fallback.

Done when: no climate number in the codebase is a literal; the answer to "has monsoon rain changed in my district since 1990?" is computed and states the method and its limits.

---

### Phase R14: Extreme-event risk classifier

**Hazards and labels**
- Heatwave day, cold-wave day, heavy-rain day, using IMD's published station criteria (verify and cite exact values in the README; for example heavy rain at or above 64.5 mm in 24 hours; heatwave at or above 40 °C with a departure of at least 4.5 °C in the plains or at or above 45 °C; cold wave at or below 10 °C with a departure of at least 4.5 °C below normal). Temperature labels from the R11 IEM station series with normals from the station's own 1991 to 2020 data; rain labels from CHIRPS at the station cell. State the gridded-rain smoothing limitation.
- **Feasibility gate before modelling:** write `ml/extreme_event/reports/eda.md` with event counts per hazard in the training and test blocks. Keep a hazard only if it has at least 50 positive station-days in training and 20 in test. Report excluded hazards honestly.

**Models**
- Stage 1 (long history, no forecast inputs): predict the event at day t+h (h = 1, 2, 3) from information available at issue time: antecedent observations (past 7 days), anomalies against training-year climatology, day-of-year, station coordinates and elevation. LightGBM with calibrated probabilities, SHAP explanations. Training years chosen by data availability (record them), chronological test block as in R11.
- Stage 2 (when R11 data is ready): add the forecast values from R11 as features, on the shorter archive period.
- Baselines: climatological frequency by station and day-of-year, persistence, and (on the Stage 2 period) "forecast exceeds the threshold".

**Metrics**: PR-AUC with prevalence stated, Brier skill score against climatology, reliability curve, recall at precision 0.5, per lead day, with block-bootstrap intervals. Report plainly if the model only ties the threshold rule.

**Output**: a risk card with probability, risk level (thresholds from validation), top three SHAP drivers, and the line "This is not an official warning." Official alerts are always shown separately and verbatim.

Done when: `get_risk_outlook` uses the model; hazards without enough events are absent, with the reason in the card.

---

### Phase R15: RAG advisory engine

**Corpus (real documents only)**
- Download public documents into `data/raw/knowledge/` (NDMA do's and don'ts and heatwave, cold wave, flood and cyclone guidance; the IMD colour-code explanation; published state heat action plans; fisherfolk safety guidance; public ICAR and state agriculture university advisories). Prefer official Hindi and regional-language versions where they exist. Record URL, licence or terms, retrieval date and sha256 in `seeds/knowledge/sources.csv`. Skip anything whose terms forbid reuse. If a download fails, set the row to `unavailable`; if downloads are blocked, stop and ask for H6.
- Extract text with page numbers (`pypdf` or HTML extraction). **No hand-written summaries and no keyword-stuffed "Key terms" lines.** Delete the current `seeds/knowledge/*.md` files and rebuild from the real sources. Chunk by headings or pages (about 300 tokens with small overlap); metadata: source, url, page, language, hazard, sha256.

**Retrieval**
- Dense: `BAAI/bge-m3` if CPU time allows, otherwise `intfloat/multilingual-e5-small`. Sparse: BM25. Hybrid by reciprocal rank fusion. Numpy cosine search is enough at this scale.
- Answering: the LLM receives retrieved chunks and must cite chunk ids; the verifier checks that cited ids exist and were retrieved. If the best score is below a threshold chosen on validation queries, answer "I don't have official guidance on that" with the relevant helplines.

**Evaluation**
- 100 human-written queries with human-marked relevant chunks (H2), split 30 validation and 70 test. Recall@1, @3, @5 and MRR for BM25-only, dense-only and hybrid, with bootstrap intervals.
- Answer quality, with and without retrieval, on the 70 test queries with real LLM calls: citation precision, numeric faithfulness (verifier), and a judge score whose agreement with humans is measured in R18.7.

Done when: advice questions use `search_knowledge`; the agromet fixture path is unreachable; the card reports the three retrieval configurations from real labels.

---

### Phase R16: Integration into the live agent

- Orchestrator: intent model routing (R12), forecast with `ml_mode` (R11), `get_climate` (R13), `get_risk_outlook` (R14), `search_knowledge` (R15). The LLM composes only from structured evidence; the verifier still gates output; the template fallback stays and is counted in the trace.
- `/v1/ml/models`, `/v1/ml/models/{id}/card`, `POST /v1/ml/predict/{id}`, `/v1/ml/eval/summary`: read only from `reports/metrics.json`; missing means `NOT MEASURED`.
- Done when: a contract test confirms that the `trace` event lists exactly the models that ran and that `enabled_in_production=false` models are never used.

### Phase R17: Visible AI and ML in the web app

- `TracePanel` in `AnswerCard`: intent and confidence, tools and sources, raw versus corrected forecast with the p10 to p90 band, risk with SHAP drivers, retrieved passages with ids, verifier result, which LLM answered.
- `features/ml-lab/`: one tab per model (problem, data sources and dates, split, metrics against baselines with intervals, figures, model card, "try it") and an evaluation tab. Values come only from `/v1/ml/*`.
- Locales for all seven Tier-1 languages and the language switcher (R1.4); Indic fonts; the axe test runs in all seven.
- Done when: every number shown comes from the API; `NOT MEASURED` renders where data is missing.

---

### Phase R18: Real evaluation

**R18.1 Golden answers** against the Orchestrator with the live LLM: per-city recorded Open-Meteo responses (`recorded_real_http`), assertions on the numbers in the answer, the named source, and the language. Report pass rate per language and intent.

**R18.2 Latency** over the real HTTP stack (`docker compose up`): at least 100 queries across languages through `/v1/chat` with live Groq and Sarvam; record time to first token and total time (p50, p95), the `llm_path` per query, and the template-fallback rate. Throttle to provider rate limits (record the throttle).

**R18.3 Load**: at 20, 50 and 100 concurrent users against the Docker stack. Run with the LLM disabled (`llm_path: disabled`, a configuration, reported separately) and with the live LLM at low concurrency (for example 5). Record the machine specification.

**R18.4 Speech**: with H3 audio, call Sarvam speech-to-text and compute WER with `jiwer`, per language. No audio means `NOT MEASURED`; a 0% result is reported as is.

**R18.5 Ablations** (each from real runs, with bootstrap intervals)
1. No tools versus tools: real LLM without tools versus with tools on the gold queries; score with the numeric verifier.
2. Tools versus tools plus retrieval: on the R15 test queries.
3. Raw NWP versus Ridge versus LightGBM: from R11 predictions.
4. Intent encoder versus LLM function calling: from R12.
5. Cascaded translation (Sarvam) versus native generation (Groq) in two languages: numeric preservation by the verifier, back-translation chrF with `sacrebleu`, and human ratings on 20 samples (H4).

**R18.6 Alert freshness**: run the real poller against the live SACHET feed for at least 48 hours; record `first_seen_at - sent` and the poll interval. Fewer than five alerts observed means `NOT MEASURED`. Report pipeline processing time (fetch to API availability) separately.

**R18.7 Judge calibration**: Groq judge versus two human raters on 30 answers (H4). Report kappa for judge against each human and human against human, as separate numbers. If judge against human is below 0.6, report human-only scores.

**R18.8 Accessibility**: keep axe-core and Lighthouse; screen-reader testing stays `NOT MEASURED` unless a human did it.

All outputs go to `eval/results/<date>/` with the audit fields from R9.2.

### Phase R19: Documentation from results

- Generate `docs/EVAL_RESULTS.md` and every `MODEL_CARD.md` from result files (T4).
- Rewrite `docs/ml-plan.md` to match what exists; update `README.md` and `docs/architecture.md`.
- Rewrite `docs/PROPOSAL_DELTAS.md` from the audited results: for each proposal objective, state target, measured value with interval, or `NOT MEASURED`, and what changed.
- Update `scripts/tasks/demo.py`: Hindi query, trace panel, ML on and off, risk card, climate trend, advice with citations, alert relay.

---

## 6. Sequencing, ownership and effort

Order: R8.1 → R8.2 → R8.3, R8.4, R8.5 → R9 → R10 → R11, R12, R13, R14, R15 (parallel; R14 Stage 2 after R11) → R16 → R17 → R18 → R19. Start the human tasks H1, H2, H3 and H6 now; they are the long poles.

| Person | Tickets |
|---|---|
| Ashwin | R8, R9, R15, R16, R18 (lead), R19; H4, H5 |
| Aman | R10, R11, R12, R14; H1 |
| Pradeep | R13, R17; H2, H3 |

Effort in person-days: R8 about 2, R9 about 2, R10 about 1, R11 about 4, R12 about 3 (plus H1), R13 about 3, R14 about 4, R15 about 3 (plus H2, H6), R16 about 2, R17 about 3, R18 about 4 (plus a 48-hour alert run), R19 about 1. Run R8 to R10 first (about 5 days), then the models in parallel (about 4 to 5 days), then integration and evaluation (about 6 days).

If time is short, cut in this order: R14 Stage 2, R14 entirely, the optional MuRIL notebook, R18.3 high-concurrency runs. Do not cut R8, R9, R11, R12, R15, R13 or R18.2; they carry the claims.

---

## 7. Definition of done (every ticket)

- Tests first and passing; `python scripts/dev.py ci` green; `python scripts/dev.py audit-results` green.
- For ML tickets: `metrics.json`, `predictions_test.csv`, `RUN_MANIFEST.json`, figures and a generated `MODEL_CARD.md` are committed, and `python scripts/dev.py ml verify <model>` passes.
- A "reproduce from scratch" section in the model README with the exact commands, expected runtime, and data volume.
- The ledger entry lists proof: command, output path, `git_sha`.
- No guard file edited in the same PR (G1).

Model card sections (generated): intended use, data (sources, dates, row counts, share of machine-generated rows), split, baselines, metrics with intervals, failure analysis (worst stations, languages or intents), limitations, ethical notes, how to reproduce.

---

## 8. Decisions already made (do not ask)

- D1 IMD is out of scope; dormant adapters stay behind the flag.
- D2 Sarvam is the primary translation and speech provider; Groq is the translation fallback; no stub anywhere user-visible.
- D3 Aviation is not supported in this pilot.
- D4 Tier-1 languages: en, hi, bn, mr, te, ta, or.
- D5 Rain truth is CHIRPS; ERA5-Land only as a labelled fallback.
- D6 Vector search is numpy cosine; no vector database.
- D7 If a model loses to its baseline, the baseline ships (S2).
- D8 The reviewed flag on translated guidance may be set only by a human (H7).

---

## Appendix A: Data sources and notes

- **Open-Meteo**: Previous Runs API (`previous-runs-api.open-meteo.com`), Historical Forecast API (`historical-forecast-api.open-meteo.com`), Archive API (`archive-api.open-meteo.com`, use `models=era5`), Geocoding API. No key for non-commercial use; batch coordinates per request; cache; respect the daily limit; attribution CC BY 4.0. Verify variable names against the current docs before coding.
- **IEM** (`mesonet.agron.iastate.edu`): ASOS and METAR for Indian airports. Confirm the Indian network id and station metadata first.
- **CHIRPS** (`data.chc.ucsb.edu`): daily 0.05° rainfall, cloud-optimised GeoTIFFs; verify the path layout and final or preliminary status.
- **NDMA SACHET** public RSS and CAP feeds (`sachet.ndma.gov.in`).
- **Sarvam** (`api.sarvam.ai`): the translation adapter currently uses model `mayura:v1` and Odia code `od-IN`; re-check the current docs and record any change in `docs/integration-notes.md`.
- **HuggingFace**: MASSIVE (`AmazonScience/massive`), `intfloat/multilingual-e5-small`, `BAAI/bge-m3`, optional MuRIL.
- **Public documents** for the knowledge base: NDMA, IMD (documents only), state disaster authorities, ICAR and agriculture universities.

## Appendix B: Fresh-context audit prompt (Ashwin runs this after each phase in a new session)

> You are an independent auditor. Do not trust any report, ledger entry or model card. For each file under `ml/*/reports/` and `eval/results/`, check: (1) the script named in `generated_by` exists and reads real input files whose sha256 matches; (2) no `random`, `numpy.random`, hard-coded metric literals, `simulate`, `synthetic`, `stub`, or fixture-only data feeds any reported number; (3) the numbers in `metrics.json` can be recomputed from `predictions_test.csv`; (4) the test block comes strictly after the training block with the stated embargo; (5) latency and load results used a live LLM or a configuration flag named `disabled`, never a stub; (6) every claim in `docs/` and `PROPOSAL_DELTAS.md` appears in a result file. List every discrepancy with file and line. Do not fix anything.

## Appendix C: Files most affected

`ml/` (all), `services/api/app/modules/{forecast,climate,advisory,alerts}/`, `services/api/app/agent/orchestrator.py`, `services/api/app/gateways/translation/`, `services/api/app/registry.py`, `services/api/tests/guards/`, `scripts/dev.py`, `scripts/tasks/{ml,audit_results,acceptance,eval,latency_report,load_test,eval_speech,translate_static}.py`, `eval/harness.py`, `eval/golden/`, `seeds/{translations,knowledge}/`, `docs/`, `apps/web/src/features/{ask,ml-lab}/`, `requirements-ml.txt`, `.github/CODEOWNERS`, `.agents/rules/`.
