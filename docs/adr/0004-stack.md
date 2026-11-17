# 0004: Stack

**Status:** accepted (6 November 2026); revised 14 November 2026 for a simpler pilot

**Context:** The data are structured and geospatial. One backend language keeps agent work consistent. A website can be driven and verified directly by browser agents and Playwright. Fewer moving parts mean fewer failures for unattended agents.

**Decision:** Python with FastAPI for services; PostgreSQL with PostGIS (Postgres full-text search for the small guidance library; pgvector only if later needed); Redis; Zarr on a local volume behind an S3-compatible path layer; a scheduled worker (APScheduler) for ingest; React with TypeScript and Vite for the website, built as a progressive web app; Docker Compose on one India-region VM for the pilot, with Kubernetes manifests added at hardening; structured JSON logs, a Prometheus metrics endpoint and a status page for observability. No MongoDB, no Node.js service in production, no native app, no Dagster for now.

**Consequences:** The pilot is cloud-agnostic and easy to run. Revisit orchestration, vector search and observability stacks when load or needs demand.
