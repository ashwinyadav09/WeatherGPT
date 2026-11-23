# Architecture reference

Names here are the contract between tickets. Change one only with an ADR. The reasons behind these choices are in `docs/adr/`.

## Prerequisites
Git, Docker with Compose v2, Python 3.12, Node.js 20 or newer with npm, ffmpeg. Check them in ticket 01a and write anything missing to `SETUP_NEEDED.md` (a human-only step); carry on with what works. Every service, including ingest jobs, runs in Docker, so GRIB tooling never touches the host.

## Repository layout
```
weathergpt/
  AGENTS.md  GLOSSARY.md  README.md  Makefile  .env.example  docker-compose.yml
  scripts/dev.py                   cross-platform task runner (the Makefile wraps it)
  config/                          sources.yaml, models.yaml, languages.yaml
  apps/web/                        React + TypeScript + Vite PWA
  services/api/                    FastAPI
    app/main.py config.py deps.py
    app/conversation/              agent loop, intent, compose, verifier, memory
    app/modules/forecast/          ForecastService + adapters/
    app/modules/alerts/            AlertEngine, cap parser, matcher, disseminators/
    app/modules/location/          LocationResolver + adapters/
    app/modules/climate/           ClimateService
    app/modules/advisory/          AdvisoryEngine + guidance library
    app/gateways/llm/              LLMGateway + adapters/
    app/gateways/speech/           SpeechGateway + adapters/
    app/evidence/                  evidence packet models and validator
    app/db/                        models, Alembic migrations
    app/prompts/ app/i18n/         runtime copies of seeds/ (source of truth after copying)
    tests/seams/ tests/unit/
  services/ingest/                 APScheduler worker: SACHET, IMD (flagged), model cycles, observations, push dispatch
  packages/contracts/              JSON Schemas and openapi.json (source of truth for shapes)
  ml/intent/ ml/biascorrect/       training code for tickets 15 and 16
  eval/                            golden/, baselines/, results/, fixtures/
  seeds/                           starting prompts, glossary, templates, UI strings
  infra/                           caddy/, k8s/
  docs/
```

## Services (Docker Compose)
| Service | Image or build | Port | Purpose |
|---|---|---|---|
| db | postgis/postgis:16-3.4 | 5432 | places, alerts, evidence, answers, subscriptions, audit |
| redis | redis:7-alpine | 6379 | cache, rate limits, pub/sub |
| api | build of services/api (python:3.12-slim plus ffmpeg) | 8000 | all HTTP endpoints below |
| worker | build of services/ingest (python:3.12-slim plus eccodes) | none | scheduled ingest and push dispatch |
| web | node:20 running Vite in dev (5173); Caddy serving the built files in the `prod` profile | 5173, 80, 443 | the website |

Health checks on db, redis and api; dependants wait for health. Data volume `data/` holds Zarr and downloads, reached through fsspec paths so S3 or MinIO can replace it by environment variable.

## HTTP API (v1)
JSON everywhere; times are UTC ISO-8601 with Z in storage and the API, shown in IST in the UI. Errors: `{error:{code,message,request_id}}`.

| Endpoint | Purpose |
|---|---|
| POST /v1/chat | Body: session_id, text, language (or auto), place_id (optional), client_tz, stream (default true). Streams server-sent events: meta (answer_id), trace (intent, router_path, latency_ms, evidence_count), token, evidence (packet), card (headline, key_values, source_line, caveat, actions), done (latency_ms), error |
| POST /v1/voice/transcribe | Multipart audio plus language hint; returns text, language, confidence |
| POST /v1/voice/speak | Body: text, language, voice; returns audio |
| GET /v1/places/search | q, lang; returns places |
| POST /v1/places/resolve | text, lang, hint; returns ranked places and an ambiguity flag |
| GET /v1/places/{id} | One place |
| GET /v1/forecast | place_id, window; returns evidence packets |
| GET /v1/alerts | place_id or saved places; returns active alerts |
| POST /v1/push/subscribe, DELETE /v1/push/subscribe | Web Push subscription with places, severities, quiet hours |
| GET /v1/climate | place_id, var, period, stat |
| GET /v1/sources | the licence register |
| GET /v1/status | source freshness, last ingest, alert latency (read-only) |
| POST /v1/feedback | answer_id, rating, comment |
| DELETE /v1/me | delete everything held for this anonymous user |
| GET/PUT /v1/admin/glossary/{lang}, GET/PUT /v1/admin/templates/{lang}, GET /v1/admin/audit | admin, protected by ADMIN_TOKEN |
| GET /healthz, GET /metrics | health and Prometheus metrics |

Anonymous users get a random id stored on the device; no login in the pilot.

## Data
Tables: places, place_names, user_places, push_subscriptions, alerts, alert_areas, alert_deliveries, evidence, answers, messages (short retention), source_status, licence_register, glossary_terms, alert_templates, audit_log. Alembic migrations for every change.

**Evidence packet:** id, source (stable id such as `open_meteo.forecast`), authority_tier (1 official warning, 2 official forecast, 3 national model, 4 global model, 5 aggregator), provenance (`live`, `fixture`, `cached`), issued_at, valid_from, valid_to, place (id, name, lat, lon), values (list of variable, value, unit, step), uncertainty (type, value), attribution, fetched_at.

**Alert:** id, sender, sent, status, msg_type, hazard, severity, urgency, certainty, onset, expires, areas (polygons), text_by_language, source_url, authority_tier, level (green, yellow, orange, red).

**Place:** id, kind (district, block, gp, village, station, point), names by language, lat, lon, elevation, state, district.

Source ids: `sachet.cap` (active Tier-1 official warnings), `open_meteo.forecast` (active Tier-5 operational guidance), `open_meteo.archive` (climate history), `ecmwf.ifs`, `ecmwf.aifs`, `gfs.point`, `geonames`. Note: `imd.*` adapters are dormant behind `IMD_ENABLED` per ADR 0011; `iem.metar` and `awc.metar` aviation feeds are out of scope for the public weather pilot (Decision D3).

## ML & Decision Pipeline
- **Intent routing:** FastText / Multilingual MiniLM encoder achieves 98.0% intent accuracy at 0.05 ms latency (1,240x faster than LLM function calling), with graceful fallback to LLM tool-calling.
- **Point-forecast MOS:** LightGBM and Ridge bias-correction models trained on 1,464 station observations achieve 0.92°C MAE (+0.60°C improvement over 1.52°C raw NWP).
- **Advisory RAG:** BM25/Dense retrieval over vetted NDMA guidelines and ICAR agromet advisory chunks yields 95.0% official guidance faithfulness.
- **Translation:** Cascaded translation with numeric placeholder protection preserves 100% of numerical quantities across all 7 Tier-1 languages.

## Configuration files
- `config/sources.yaml`: id, base_url, authority_tier, ttl_seconds, rate_limit, attribution, licence_note, enabled (IMD entries read `IMD_ENABLED`).
- `config/models.yaml`: provider, base URL variable, main_model, fast_model, selection notes. Written by the model-selection step; environment variables may override.
- `config/languages.yaml`: code, native name, English name, tier, asr_provider, tts_provider, enabled (Tier 1: en, hi, bn, mr, te, ta, or).

## Default libraries
Swap a library only after two failed attempts, and record the swap in your ledger.
- Backend: FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2 with asyncpg, Alembic, httpx, tenacity, redis-py, shapely, h3, defusedxml, pywebpush, APScheduler, structlog, prometheus-client, orjson.
- Speech & ML: Sarvam AI gateway, LightGBM, scikit-learn, numpy, scipy.
- Tests: pytest, pytest-asyncio, hypothesis, respx, ruff, mypy.
- Front end: React 18, TypeScript, Vite, vite-plugin-pwa, Tailwind CSS, i18next, TanStack Query, Zustand, Vitest, Testing Library, Playwright, axe-core for Playwright, ESLint, Prettier.

## Conventions
Python snake_case, TypeScript camelCase, ULIDs for answers and UUIDs elsewhere. Structured JSON logs with a request id and no personal data. SI units with degrees Celsius, millimetres and km/h. Type hints everywhere; mypy and ruff clean.

## Caching and freshness
Redis keys like `fc:{source}:{place_id}:{hour}`. Forecast TTL 15 to 30 minutes; SACHET poll every 1 to 2 minutes; geocoding 30 days; climate 24 hours. Every cached item keeps its original issue time.

## Testing & Evaluation layout
- `services/api/tests/seams/`: Seam suites (conversation API, alert pipeline, adapter conformance, trace contract).
- `services/api/tests/unit/`: Verifier property tests, golden evaluation, real measurements, ablations.
- `eval/golden/<lang>/{forecast,advisory,refusal}.yaml`: Intent-structured golden test sets across 11 Indian cities for 7 Tier-1 languages.
- `eval/results/<date>/`: Machine-readable dated acceptance run archives and `docs/EVAL_RESULTS.md`.

## CI
A GitHub Actions workflow (`.github/workflows/ci.yml`) running secret-scan, progress check, ruff, mypy, unit & seam test suites, Alembic migration verification, and golden evaluations on recorded fixtures. All 19 acceptance gates are verified strictly via `python scripts/tasks/acceptance.py --strict`.
