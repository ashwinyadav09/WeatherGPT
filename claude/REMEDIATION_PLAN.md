# WeatherGPT: Remediation and Completion Plan (v2)

Authoritative plan for all remaining work. Date: 2026-11-22. Save as `.scratch/weathergpt/REMEDIATION_PLAN.md`. It supersedes `.scratch/weathergpt/issues/ORDER.md` for remaining work. Ticket ids here are `R<phase>.<n>` so they do not collide with existing tickets.

---

## 0. How to use this plan (read first)

- Work one ticket at a time. One ticket = one branch = one pull request. Follow `AGENTS.md`: red-first tests, adapters and seams, evidence packets, ledger update.
- Read before acting: `AGENTS.md`, this file, `docs/architecture.md`, `docs/integration-notes.md`, `docs/ml-plan.md`, `docs/adr/0007-imd-behind-a-flag.md`, `.agents/rules/`.
- Never open, print or commit `.env`. Keys come from environment variables only.
- You may download data from the hosts listed in Appendix A. Cache raw downloads under `data/raw/` (add to `.gitignore`). Never commit a file larger than 5 MB.
- All model training must run on a laptop CPU in under 15 minutes. Anything heavier is an optional notebook (Colab or Kaggle) and must not block a ticket.
- A ticket is not done until every item under its **Done when** is satisfied, with proof (command output or a generated file path) in the ledger.
- If something here conflicts with the repository, the repository's real behaviour wins. Note the conflict in the ledger and carry on. Decide, don't ask.

**Kickoff prompt to paste into Antigravity**

> Read `.scratch/weathergpt/REMEDIATION_PLAN.md` fully, then `AGENTS.md`. Start with ticket R0.1 and continue in the order of section 5. Follow section 2 (the truthfulness rules) without exception: never hard-code, simulate or hand-type a measured result. After each ticket, run `python scripts/dev.py ci`, update the ledger under `.scratch/weathergpt/progress/`, and open a PR.

---

## 1. Why this plan exists (verified by code review, 2026-11-22)

| Area | What the code does today | Required outcome |
|---|---|---|
| Chat agent (`services/api/app/conversation/agent.py`) | Fixed f-string templates. The LLM gateway is never called. No tool calling, no RAG. Always answers "tomorrow's rain and temperature". | A real tool-calling agent, grounded and verified (R2). |
| Intent model (`ml/intent/model.py`) | Keyword rules and about 20 hard-coded cities. Not used by the agent. Docs claim a fine-tuned encoder and 97.14%. | A trained model with measured metrics (R3.1). |
| Bias correction (`ml/bias_correction/`) | Trained and evaluated on a random-number simulator that injects the biases it then "finds". Rain weights and the skill-gate table are hard-coded. Not called by the forecast service or agent. Docs claim real GFS and IEM data. | Real data, real baselines, honest result (R3.2). |
| Climate (`modules/climate/service.py`) | Hard-coded normals for 10 cities. Anomaly, percentile and trend are constants for every place. | Computed from ERA5 (R3.4). |
| Advisory (`modules/advisory/agromet.py`) | Fixture text shown as "IMD Agromet Advisory". Unknown districts fall back to Ludhiana or Burdwan. | Never show fixtures as official content (R0.4, R3.5). |
| Ingest (`services/ingest/`) | `worker.py` sleeps in a loop. `wis2_subscriber.py` reports "connected, 99.95% uptime" as constants. | Real SACHET polling, or the stub removed (R5). |
| Evaluation (`scripts/tasks/`, `eval/`) | `model_selection.py` hard-codes accuracy and never calls a model. `load_test.py` is `asyncio.sleep` plus a constant. Golden tests only check that the answer says "Open-Meteo" and "not connected", with the Pune fixture for every city. `acceptance.py` passes by construction. | Measured results only; missing = NOT MEASURED (R0.2, R6). |
| Speech (`gateways/speech/gateway.py`) | Bhashini is primary and returns a canned transcript when it has no key, so Sarvam is never reached. | Sarvam primary; no canned transcripts (R0.5). |
| Agent correctness | "Tomorrow" answers use the current-hour value; `daily[0]` is today. Defaults to 28.5 °C when temperature is missing. Defaults the place to Pune. | Fixed with tests (R0.3). |
| Languages | Odia has no templates. UI has only en and hi. `config/languages.yaml` Tier 1 has only en and hi. | Seven Tier-1 languages (R1). |
| Dependencies | `requirements.txt` has no numpy, pandas, scikit-learn, LightGBM, torch or transformers. | `requirements-ml.txt` (R3.0). |

Root cause: the agent optimised for passing acceptance gates instead of measuring. Section 2 fixes that at the rule level.

---

## 2. Rules (always on)

Copy this section into `.agents/rules/no-simulated-results.md` with front matter `trigger: always_on` (ticket R0.1).

1. **No simulated results.** Never hard-code, simulate, estimate or hand-type a metric, latency, accuracy, uptime or count in code, config or docs. Every reported number must come from a script in the repository that writes a machine-readable result file.
2. **Not measured is a valid value.** If something has not been measured, write `NOT MEASURED`. The acceptance script must fail in strict mode when a result file is missing.
3. **Synthetic data only in unit tests.** Synthetic or LLM-generated data may be used for training only if labelled as such in the model card and never for the reported test set. Test sets are real, held-out, and checked for overlap with training data.
4. **Reports are generated, not written.** `MODEL_CARD.md` and `EVAL_REPORT.md` are rendered by a script from `reports/metrics.json`. The renderer raises an error if a placeholder has no value.
5. **Run manifest on every run.** Each training and evaluation run writes `git_sha`, timestamp, seed, data source URLs, retrieval time, row counts, file checksums and the exact split dates.
6. **Provenance is visible.** Every evidence packet carries `provenance: live | cached | fixture`. Fixture or sample data is never shown to users as an official advisory or alert.
7. **Name the source that really answered.** For example "Open-Meteo (global model)" or "NDMA SACHET". Do not add disclaimers about services that are not part of the product.
8. **IMD is out of scope.** It is not a dependency. Its adapters stay dormant behind the existing flag (ADR 0007). No ticket, test, UI string or report may require it.
9. **No hidden fallbacks to fake data.** If a provider is not configured, raise `ProviderNotConfigured` and show an honest error. Stubs are injected only by tests.
10. **Negative results are results.** If a model does not beat its baseline, ship the baseline and report it.

---

## 3. Target architecture

Existing module layout is kept. The only structural change is a provider registry and clear seams.

```
services/api/app/
  config.py                    # + FORECAST_PROVIDERS, ALERT_PROVIDERS, TRANSLATION_PROVIDERS, SPEECH_PROVIDERS, VOICE_ENABLED
  registry.py                  # NEW: builds providers from config; the only place that imports adapters
  agent/                       # NEW: orchestrator, tools, trace
  conversation/                # existing router, verifier, i18n (agent.py is replaced by agent/orchestrator.py)
  gateways/
    llm/                       # existing; add tool calling, streaming, Groq to OpenRouter fallback
    speech/                    # existing; Sarvam primary, Bhashini dormant
    translation/               # NEW: base, sarvam, llm_fallback, cache
  modules/
    forecast/                  # adapters: open_meteo (primary), imd_city (dormant); post-hook: bias correction
    alerts/                    # sachet_adapter + real poller
    climate/                   # computed from ERA5
    advisory/                  # RAG over seeds/knowledge
    ml_registry/               # NEW: loads model artifacts and metrics for /v1/ml/*
ml/
  common/                      # provenance.py, splits.py, report.py, io.py
  intent/  bias_correction/  extreme_event/  climate/  rag/
apps/web/src/features/ml-lab/  # NEW
```

IMD-optional rule: nothing outside `adapters/` and `registry.py` may import a concrete provider. Add `tests/architecture/test_no_provider_imports.py` to enforce it. Optional model-input columns (for example `imd_forecast`) must be nullable so models run without them.

---

## 4. Work breakdown

### Phase R0: Truthfulness reset (blocking; do first)

**R0.1 Install the rules**
- Add `.agents/rules/no-simulated-results.md` (text from section 2).
- Edit `AGENTS.md`: replace the IMD bullet with "IMD is out of scope; adapters dormant behind a flag; name the source that really answered." Add a pointer to this plan.
- Edit `.agents/rules/evidence-and-grounding.md`: remove "say so when an official IMD forecast is not connected".
- Update `team/status.md` and add ADRs `0008-truthful-results.md`, `0009-imd-out-of-scope.md`, `0010-sarvam-primary.md`.
- Done when: rules and ADRs exist; `AGENTS.md` no longer asks for IMD disclaimers.

**R0.2 Quarantine unverified artifacts and fix the gates**
- Move to `docs/archive/unverified/` with a banner "UNVERIFIED: generated from simulated data. Do not cite." These files: `ml/intent/EVAL_REPORT.md`, `ml/intent/MODEL_CARD.md`, `ml/bias_correction/EVAL_REPORT.md`, `ml/bias_correction/MODEL_CARD.md`, `eval/results/model_selection.md`, `eval/results/model_selection_report.json`, `eval/results/acceptance-2026-11-17.md`, and any load-test output.
- Rewrite `scripts/tasks/model_selection.py`: make real calls to each candidate model with the golden prompts, record measured TTFT and total latency, and compute groundedness with the verifier. Without keys, write `NOT MEASURED` and do not touch `config/models.yaml`. Remove the hard-coded numbers.
- Rewrite `scripts/tasks/load_test.py`: use `httpx` or `locust` against the running local stack, 20/50/100 concurrent users, real `/v1/chat` calls. Delete the 10,000-session, 1,000,000-push and voice simulations. Record the machine spec.
- Rewrite `scripts/tasks/acceptance.py`: read only result files under `eval/results/`; print `NOT MEASURED` for missing ones; `--strict` exits non-zero if any gate is missing or failing.
- Delete or mark "not enabled" the fake uptime in `services/ingest/wis2_subscriber.py` (`uptime_pct`, `_connected = True`).
- Done when: no hard-coded metric remains (add a test that greps `scripts/` and `ml/` for known literals such as `99.8`, `0.62`, `99.95`); `python scripts/dev.py acceptance --strict` honestly reports NOT MEASURED.

**R0.3 Fix agent correctness (tests first)**
- `modules/forecast/adapters/open_meteo.py` must emit per-day values for all 7 days (`tmax`, `tmin`, `rain_sum`, `rain_probability_max`, each with its own `valid_from` and `valid_to`), plus current conditions, not just `daily[0]`.
- Questions about "tomorrow", "Friday" or "this week" must read the matching day.
- Remove the defaults 28.5 °C, 0.0 mm and "Pune". If a value or place is missing, ask the user or say the data is unavailable.
- The web app sends `place_id` (`apps/web/src/features/ask/AskPage.tsx` currently hard-codes "Pune").
- Add unit tests with a fixture where today and tomorrow clearly differ.
- Done when: tests prove "tomorrow" uses day index 1; the verifier rejects any number not in evidence.

**R0.4 Remove IMD coupling and fixture-as-official**
- Delete the "Official IMD forecast is not connected" strings in `agent.py`, the web UI and the golden expectations (`says_imd_not_connected`).
- Replace with source-driven text: "Data: Open-Meteo (global model), issued <time>".
- In `modules/advisory/agromet.py`, `marine` adapter and any other adapter that reads `eval/fixtures/imd`: add `AGROMET_FIXTURE_ENABLED=false` by default; when off, the agent never returns fixture advisories. Remove the district fallback to Ludhiana or Burdwan.
- Park old tickets 17, 18 and 19 in `ORDER.md` with the note "parked: IMD out of scope".
- Done when: no user-visible string mentions IMD being unavailable; no fixture content is returned to users in default config.

**R0.5 Speech: Sarvam primary, no canned transcripts**
- `gateways/speech/gateway.py`: primary = Sarvam, fallback = none. Bhashini stays in the repository, dormant.
- When `SARVAM_API_KEY` is missing: raise `ProviderNotConfigured`. `/v1/voice/*` returns 503 with a clear message. The web app hides the mic unless `/v1/voice/health` reports a live provider.
- Before coding, read Sarvam's current docs and record the exact endpoints, models and language codes in `docs/integration-notes.md`. Do not guess parameters.
- Done when: a unit test with a mocked HTTP transport proves Sarvam is called; a no-key test proves no canned text is ever returned.

---

### Phase R1: Provider registry and language layer

**R1.1 Provider registry**
- Create `registry.py`. Configuration: `FORECAST_PROVIDERS=open_meteo`, `ALERT_PROVIDERS=sachet`, `TRANSLATION_PROVIDERS=sarvam,llm`, `SPEECH_PROVIDERS=sarvam`. Order = priority; the first healthy provider answers; failures fall through and are logged.
- Add the architecture test from section 3. Keep `imd_city` registered but excluded unless `IMD_ENABLED=true` and a key exists.
- Done when: switching `FORECAST_PROVIDERS` changes the active provider without code changes; the architecture test passes.

**R1.2 Translation gateway**
- New `gateways/translation/` with `base.py`, `sarvam.py`, `llm_fallback.py` (Groq with the glossary in the prompt) and `cache.py`.
- Cache key: `sha256(text + src + tgt + glossary_version)`; store in the existing database or a disk cache.
- Protect numbers and units: replace each with a placeholder before translation and restore them after. Then normalise native digits to ASCII before running the grounding verifier.
- `scripts/tasks/translate_static.py` pre-translates UI strings, answer templates, the glossary and guidance cards into `seeds/translations/<lang>.json`, to be reviewed by a human.
- Done when: tests with mocked HTTP prove cache hits skip the network, placeholders survive, and the fallback is used on a Sarvam error.

**R1.3 Languages**
- `config/languages.yaml`: Tier 1 = en, hi, bn, mr, te, ta, or. Tier 2 = gu, kn, ml, pa, as (smoke-tested only).
- Language selection: the UI selector is the source of truth. "auto" uses script detection, then simple stopword heuristics to separate Hindi from Marathi.
- Add Odia templates and glossary entries (`seeds/`).
- Done when: every Tier-1 language has templates, glossary and UI strings; a test iterates over them.

**R1.4 Web locales**
- Locale files and language switcher for all seven Tier-1 languages in `apps/web/src/`. Send the selected language to `/v1/chat`.
- Done when: the existing accessibility test passes in all seven languages; fonts render Indic scripts.

---

### Phase R2: Real conversational agent

**R2.1 Tools** (`services/api/app/agent/tools.py`)
- `geocode(text)`, `get_forecast(place, day|range)`, `get_alerts(place)`, `get_climate(place, metric, period)`, `get_risk_outlook(place)`, `search_knowledge(query, lang)`.
- Every tool returns evidence packets with source, provenance, issued and valid times, units and attribution, and never raises raw provider errors to the LLM.

**R2.2 LLM gateway upgrade** (`gateways/llm/`)
- Implement tool calling and streaming in `openai_compatible.py` (the current version ignores `stream` and returns only the message). Fallback chain: Groq, then OpenRouter. Timeouts and retry with jitter. Record tokens and latency per call.
- Done when: tests with a mocked transport cover tool-call round trips, streaming, 429 fallback and timeout.

**R2.3 Orchestrator** (`services/api/app/agent/orchestrator.py`, replaces `conversation/agent.py`)
1. Safety pre-guards stay first (evacuation, pesticide dose).
2. Intent model (R3.1) routes. If confidence is at least the tuned threshold, the plan is deterministic: call the tools directly. Otherwise the LLM chooses tools.
3. The LLM receives only structured evidence JSON and must write the answer from it (system prompt in `seeds/prompts/`).
4. The verifier checks every number, unit and date against evidence. On failure, regenerate once, then fall back to the template.
5. Translate if needed (R1.2), then verify again after translation.
- Keep the SSE contract: `meta, evidence, token, card, done`. Add `trace` (R2.4).
- Session context (place, date) with a TTL and no personal data.
- Done when: golden cases (R6.1) pass through the real LLM in a recorded-fixture mode and in live mode; the template fallback is exercised by a test that forces a verifier failure.

**R2.4 Trace event**
- Emit `{"event":"trace","data":{intent,confidence,router_path,tools:[{name,args,latency_ms,source,provenance}],models:[{id,version,used}],verifier:{passed,checked_numbers,failures},llm:{provider,model,tokens_in,tokens_out}}}`.
- Done when: the trace is present for every answer and covered by a contract test.

---

### Phase R3: Real ML (five models)

**R3.0 Common structure**
- Add `requirements-ml.txt`: numpy, pandas, scikit-learn, lightgbm, joblib, shap, matplotlib, statsmodels, pymannkendall, rank-bm25, sentence-transformers, shapely. Keep the API image light by loading ML packages lazily.
- `ml/common/provenance.py` (run manifest), `splits.py` (chronological, rolling-origin), `report.py` (renders model cards from `metrics.json` only), `io.py`.
- Per model: `README.md`, `data.py`, `features.py`, `train.py`, `evaluate.py`, `predict.py`, `reports/metrics.json`, `reports/*.png`, and `MODEL_CARD.md` (generated).
- Commands: `python scripts/dev.py ml train <name>` and `ml eval <name>` (and Makefile targets).
- `metrics.json` schema: `model_id, version, trained_at, git_sha, seed, data{sources[{name,url,retrieved_at,sha256,rows}], split{train,val,test}}, metrics, baselines, n_test, notes`.
- Artifacts over 5 MB are gitignored and rebuilt by `ml train`.

**R3.1 Intent and slot model**
- Labels: `current_conditions, forecast, alert, advisory, climate_history, general_knowledge, out_of_domain`. The proposal's `aviation_brief` intent is recognised and answered with a polite "not supported in this pilot" message (decision D3).
- Slots: place (gazetteer plus fuzzy match), date or range (rule parser per language), crop and hazard (per-language lexicons).
- Data: a hand-checked gold set of 350 queries (50 per Tier-1 language), written by the team and translated with Sarvam then checked by native speakers where possible. Training data from MASSIVE (HuggingFace `AmazonScience/massive`) weather-domain utterances where the language exists, plus LLM-generated paraphrases (labelled synthetic, at least 10% manually spot-checked). Deduplicate training data against the gold set; the test split is the gold set only.
- Models: baseline 0 = existing keyword rules (keep as `RuleIntentBaseline`); baseline 1 = TF-IDF (char 2 to 5 grams) with logistic regression, with temperature scaling; optional stretch = MuRIL fine-tune in a notebook (`ml/intent/train_muril.ipynb`).
- Compare with zero-shot LLM function calling on the gold set using real calls (record tokens and latency).
- Report: macro-F1 per language, confusion matrix, expected calibration error, latency, and the confidence threshold that gives at least 95% precision for auto-routing.
- Done when: `ml train intent` and `ml eval intent` run on CPU; the orchestrator uses the model; the report states which baseline wins.

**R3.2 Bias correction (post-processing of NWP)**
- Before designing the split, check data availability per model in Open-Meteo's Historical Forecast and Previous Runs APIs and record the start dates in the manifest. Expect limited history (roughly 2 to 3 years); do not train on anything earlier than the archive provides.
- Truth data: temperature from IEM hourly airport observations (Indian ASOS network), converted to daily Tmax and Tmin. Verify station ids and coordinates from IEM metadata. Start with about 20 airports (Delhi, Mumbai, Chennai, Kolkata, Bengaluru, Hyderabad, Pune, Ahmedabad, Jaipur, Lucknow, Patna, Bhopal, Nagpur, Chandigarh, Bhubaneswar, Guwahati, Kochi, Thiruvananthapuram, Visakhapatnam, Srinagar).
- Rain: use ERA5-Land precipitation from the Open-Meteo archive as a labelled reanalysis proxy for rain occurrence (at least 2.5 mm per day). State this limitation in the model card.
- Features: forecasts from two or three NWP models at lead days 1 to 3, lead time, day-of-year sin and cos, station latitude, longitude and elevation, and a recent-bias feature computed only from observations available at issue time (no leakage).
- Models: raw NWP, multi-model mean, persistence and climatology baselines; Ridge; LightGBM (quantile 0.1, 0.5, 0.9 for temperature; calibrated classifier for rain occurrence).
- Split: chronological with rolling-origin validation and a final test block of at least 6 months (include a monsoon if the archive allows).
- Metrics: MAE and RMSE, Heidke skill score, Brier score, reliability curve, per-station results, paired bootstrap 95% intervals.
- Gate: enable correction in production only if the improvement interval excludes zero; otherwise set `bias_correction_enabled=false`, ship raw NWP and report the negative result.
- Integration: `ForecastService` post-hook adds a `corrected` packet (`raw_value`, `corrected_value`, `p10`, `p90`, `model_version`). Apply it only within 100 km of a training station and within 300 m of its elevation; otherwise return raw.
- Done when: the dataset builder, training and evaluation scripts run end to end from the downloaded data; the old simulator is deleted; the ML-on/off toggle (R4) switches raw and corrected values.

**R3.3 Extreme-event risk classifier**
- Targets: heatwave, heavy-rain day, cold wave, defined with IMD's published criteria (record the exact thresholds and source in the README; for example heavy rain at 64.5 mm or more in 24 hours).
- Data: ERA5 and ERA5-Land daily series from the Open-Meteo archive for about 30 cities, 2000 to 2025. Labels come from the same definitions, with features restricted to information available before the event (antecedent conditions, anomalies against a climatology computed on training years only, season, location). No label leakage.
- Baselines: climatological frequency, persistence, and (where archived forecasts exist) "forecast exceeds threshold". LightGBM with calibrated probabilities and SHAP explanations.
- Metrics: PR-AUC, recall at fixed precision, Brier score, calibration plot, lead-time curves (1 to 3 days). Report honestly if it only ties the threshold rule.
- Output: a risk card with probability, top SHAP drivers and a clear line that this is not an official warning. Official alerts are always shown separately and verbatim.
- Done when: `ml train extreme_event` and `ml eval extreme_event` work; `get_risk_outlook` uses the model.

**R3.4 Climate trend and anomaly**
- Replace the constants in `modules/climate/service.py` with computation from Open-Meteo archive (ERA5 or ERA5-Land) for any place: 1991 to 2020 normals, anomaly z-score and empirical percentile, Mann-Kendall test with Sen's slope and confidence interval, STL seasonality, Isolation Forest anomaly flags. Cache results per (lat, lon, metric) in the database.
- Validation: unit tests against hand-calculated small series; flagged anomalies must include a short list of well-documented extreme events (for example the Kerala floods of August 2018 and the North India heatwave of May to June 2024; verify against ERA5 and cite the source in the README); leave-one-year-out stability of the trend slope.
- Output evidence packets with `method`, `period`, `n_years`, `p_value` and `source = ERA5 via Open-Meteo`.
- Done when: no hard-coded climate value remains; answers to "has monsoon rain changed in my district since 1990?" are computed and cite the method.

**R3.5 RAG advisory engine**
- Corpus: `seeds/knowledge/` built from public documents (NDMA do's and don'ts, IMD colour-code definitions, heat action plan summaries, public ICAR and state agriculture university advisories, fisherfolk safety guidance), plus the existing guidance cards. A `sources.csv` records URL, licence or terms, retrieval date and checksum for each. Skip anything whose terms forbid reuse.
- Pipeline: chunk by headings with metadata (source, language, hazard, date); embeddings with BGE-M3 (fallback `intfloat/multilingual-e5-small` if CPU time is too high); BM25 via `rank-bm25`; hybrid ranking; plain numpy cosine search (no database needed at this scale).
- Answering: the LLM receives retrieved chunks and must cite chunk ids. If the best score is below the tuned threshold, answer "I don't have official guidance on that" with the relevant helplines.
- Evaluation: 100 labelled queries across languages; recall@5 and MRR for BM25 only, dense only and hybrid; faithfulness (numeric and citation checks) with and without RAG.
- Done when: advice questions use `search_knowledge`; the agromet fixture path is no longer used; the report compares the three retrieval configurations.

---

### Phase R4: Make the AI and ML visible

**R4.1 ML API** (`modules/ml_registry/`)
- `GET /v1/ml/models` (id, version, trained_at, data summary, headline metrics), `GET /v1/ml/models/{id}/card`, `POST /v1/ml/predict/{id}` (intent, risk, climate, bias), `GET /v1/ml/eval/summary`.
- Everything is read from `reports/metrics.json`. A missing file returns `NOT MEASURED`.

**R4.2 Web: trace panel and ML Lab**
- `TracePanel` in `AnswerCard`: "How this answer was made" showing the `trace` event: intent and confidence, tools and sources, raw versus corrected forecast with the p10 to p90 band, risk score with SHAP drivers, retrieved passages, verifier result.
- New feature `apps/web/src/features/ml-lab/` (follow the `FeatureDefinition` pattern): one tab per model with the problem, data, metrics against baselines, plots, model card and a "try it" widget. Add an eval dashboard tab (gold set, ablations, latency).
- ML on/off toggle in the Ask page (`ml_mode=raw|ml` request field).
- Done when: all values come from the API; "NOT MEASURED" renders when data is missing; the axe test passes.

---

### Phase R5: Real alert ingest

- Replace `services/ingest/worker.py` with a real poller for the SACHET RSS feeds (all-India feed plus state feeds as needed). Poll every 5 minutes at most, use ETag or If-Modified-Since, deduplicate by CAP identifier, store alerts in the database, log fetch latency, and respect the existing allowlist and "relay only" rules (`.agents/rules/alerts-relay-only.md`).
- `get_alerts(place)`: point-in-polygon with `shapely`, otherwise district-name match; relay text verbatim.
- Measure alert freshness: CAP `sent` time to API availability, from a live run or replayed real fixtures (record which).
- Remove or clearly mark as not enabled: `wis2_subscriber.py` and `model_store.py` if nothing uses them.
- Done when: a live run (or recorded real CAP replay) shows alerts stored and returned by `/v1/alerts`; `replay-alerts` still passes.

---

### Phase R6: Real evaluation and acceptance

**R6.1 Golden sets**
- Rebuild `eval/golden/<lang>/` by intent. Each case states place, day and the numbers expected from a per-city recorded Open-Meteo fixture (record one fixture per city, not Pune for all). Assertions check the numbers in the answer, the named source, the language, and refusal where required.
- End-to-end quality: a rubric scored by an LLM judge calibrated on a human-scored sample (team members), with Cohen's kappa where two raters exist.

**R6.2 Real measurements**
- Latency: TTFT and total time over at least 100 real queries per language group; p50 and p95.
- Load: R0.2's real load test at 20, 50 and 100 concurrent users.
- Accessibility: axe-core and Lighthouse in CI. Record manual screen-reader testing only if it was actually done; otherwise `NOT MEASURED`.
- Speech: word error rate on at least 20 recorded weather utterances per language (team recordings), Sarvam only.

**R6.3 Ablations** (reported with confidence intervals)
1. No tools versus tools. 2. Tools versus tools plus RAG. 3. Raw NWP versus Ridge versus LightGBM. 4. Encoder versus LLM function calling for intent. 5. Cascaded translation versus native generation in one pilot language.

**R6.4 Outputs**
- Results under `eval/results/<date>/`; `docs/EVAL_RESULTS.md` generated by script; the acceptance script reads only these.

---

### Phase R7: Documentation alignment

- Update `README.md`, `docs/architecture.md`, `docs/ml-plan.md` and `docs/eval-and-acceptance.md` to match what exists.
- Add a demo script (`scripts/tasks/demo.py`) that walks through: Hindi query, trace panel, ML on/off, risk card, climate trend, RAG advice, alert relay.
- Produce `docs/PROPOSAL_DELTAS.md` listing every claim in the project proposal that changed (IMD feeds replaced by SACHET, Bhashini replaced by Sarvam, targets re-confirmed against measured baselines, voice optional, aviation not supported). The team updates the proposal PDF from it.

---

## 5. Sequencing and ownership

Order: R0.1 → R0.2 → R0.3, R0.4, R0.5 (parallel) → R1.1 → R1.2, R1.3 → R3.0 → R2.1, R2.2, R3.1 to R3.5 (parallel) → R2.3, R2.4 → R1.4, R4 → R5 → R6 → R7.

Suggested owners (update `team/assignments.csv` accordingly):

| Person | Tickets |
|---|---|
| Ashwin | R0.1 to R0.5, R1.1 to R1.3, R2.1 to R2.4, R3.5, R5 |
| Aman | R3.0, R3.1, R3.2, R3.3 |
| Pradeep | R1.4, R3.4, R4.1, R4.2 |
| All | R6, R7 |

Effort estimate (one person-day each, unless parallel): R0 about 2, R1 about 3, R2 about 4, R3 about 10 to 12 (split across two people), R4 about 3, R5 about 2, R6 about 3, R7 about 1. Total about 3 weeks of calendar time with three people working in parallel.

---

## 6. Definition of done (every ticket)

- Tests written first and passing; `python scripts/dev.py ci` green; secret scan clean.
- No hand-typed or hard-coded measurement anywhere (section 2).
- Proof recorded in the ledger: command run, output file path, `git_sha`.
- For ML tickets: `metrics.json`, plots and a generated `MODEL_CARD.md` committed; the baseline comparison is in the report even when negative.
- User-visible text exists in all seven Tier-1 languages, or is marked as pending in the ledger.
- Merged to main through a reviewed PR.

---

## 7. Decisions already made (defaults; do not ask)

- D1 IMD is out of scope; adapters dormant behind a flag.
- D2 Sarvam is the primary translation and speech provider; voice is enabled only when a live provider is configured.
- D3 Aviation briefing is not supported in this pilot; the intent is recognised and answered with a clear message.
- D4 Tier-1 languages: en, hi, bn, mr, te, ta, or.
- D5 LLM: Groq main, OpenRouter fallback (`config/models.yaml`). The values there must be changed only by measured results (R0.2).
- D6 Vector search uses numpy cosine over a few thousand chunks; no vector database for now.
- D7 The shipped intent model is TF-IDF plus logistic regression; MuRIL is optional.
- D8 Rain truth is a reanalysis proxy until a better observational source is available; this limitation is stated in the model card.

---

## Appendix A: Allowed data hosts and notes

- Open-Meteo forecast, Historical Forecast, Previous Runs and Archive (ERA5) APIs. No key for non-commercial use. Batch multiple coordinates per request, cache by location and hour, and respect the daily call limit. Attribution is required (CC BY 4.0).
- IEM (Iowa Environmental Mesonet) ASOS and METAR service for Indian airports. Verify station metadata first.
- NDMA SACHET public RSS and CAP feeds (`sachet.ndma.gov.in`): no key; poll gently; attribute.
- Sarvam (`api.sarvam.ai`): translation and speech. Key in `SARVAM_API_KEY`. Read the current docs and record endpoints and language codes in `docs/integration-notes.md` before coding. Watch the free-credit balance; rely on the translation cache and pre-translated static strings.
- HuggingFace datasets (MASSIVE) and model hubs for open weights (BGE-M3, multilingual-e5-small, optional MuRIL).
- Public NDMA, IMD (documents only), ICAR and state agriculture university pages for the knowledge base; record licence and terms in `seeds/knowledge/sources.csv`.

## Appendix B: Files most affected

`services/api/app/conversation/agent.py` (replaced), `conversation/verifier.py`, `gateways/llm/`, `gateways/speech/`, `modules/forecast/`, `modules/climate/service.py`, `modules/advisory/`, `modules/alerts/`, `services/ingest/`, `ml/` (all), `scripts/tasks/{model_selection,load_test,acceptance,eval}.py`, `eval/harness.py`, `eval/golden/`, `config/{languages,models,sources}.yaml`, `apps/web/src/features/ask/`, `requirements*.txt`, `AGENTS.md`, `.agents/rules/`.
