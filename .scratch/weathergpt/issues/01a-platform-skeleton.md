# 01a: Platform skeleton

**What to build:** A developer or agent can clone the repository, run `python scripts/dev.py doctor`, start the whole stack with one command, run every test with one command, and see CI pass on GitHub. The stack answers a health check. The evidence packet, alert, place and answer shapes exist as machine-checkable contracts with an exported OpenAPI file. Every module in docs/architecture.md exists as an interface with a stub or a minimal adapter, and extension points let other people add modules, adapters and pages without editing shared files. A golden-set harness runs a one-case dummy set end to end.

**Blocked by:** None (can start immediately)

**Owner:** ashwin | **Reviewer:** aman

**Status:** ready-for-agent

- [ ] Docker Compose with db, redis, api, worker and a web service stub, with health checks; the starter `scripts/dev.py` is extended through `scripts/tasks/` so up, down, test, lint, eval, replay-alerts, contracts, ci, acceptance, contract-checks and demo all work
- [ ] API skeleton: healthz and metrics endpoints, structured logs with a request id, configuration from the environment and `config/*.yaml`, the error shape from docs/architecture.md
- [ ] Database: an Alembic baseline with PostGIS enabled and the tables the first tickets need; the db-heads task enforces a single migration head
- [ ] Contracts: JSON Schemas for the evidence packet, alert, place and answer events, an exported `openapi.json`, and a validator that tests use
- [ ] Interfaces with stubs: ForecastService (adapters registered from `config/sources.yaml`), AlertEngine, LocationResolver (with a minimal Open-Meteo geocoding adapter), ClimateService, AdvisoryEngine, SpeechGateway, LLMGateway (a stub adapter and an OpenAI-compatible adapter skeleton), GroundingVerifier
- [ ] Extension points: routers discovered from each module's router file, adapters from config; documented in docs/architecture.md
- [ ] A golden-set harness that runs a dummy case and writes a report, a replay harness skeleton, and a licence register with a sources endpoint
- [ ] The CI workflow passes on GitHub (lint, tests, secret scan, one migration head) using recorded fixtures only
- [ ] `.env.example` matches the code and no secrets are committed
- [ ] The three seam test suites exist, each with at least one passing test
