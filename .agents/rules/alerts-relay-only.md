---
trigger: model_decision
description: Apply when writing or changing anything that ingests, matches, translates, formats or sends an alert, warning, advisory or notification.
---

# Alerts: relay official, never write

- Show official alerts as issued, with sender, issue time and expiry. Build alert wording from vetted templates keyed by hazard, severity and action; fill only place and time.
- Keep the LLM out of the alert path. A test asserts that no LLM call occurs between ingest and push.
- CAP: polygons arrive as lat,lon; convert to lon,lat for GeoJSON. Ignore Test and Exercise statuses in production and log them for drills. Resolve Update and Cancel through references. Accept only allowlisted sender domains.
- IMD colour codes differ by endpoint: the nowcast APIs run 1 green to 4 red; the district warning API runs 1 red to 4 green. Map each endpoint explicitly and keep a test per mapping.
- IMD times mix UTC, IST and HHmm. Parse each field with an explicit rule.
- Point to official guidance and local authorities for evacuation or stay decisions; leave the decision to them.
- Keep model-derived heads-ups out of the pilot. If added later, style them distinctly from official alerts, avoid alert colours and pass legal review.
