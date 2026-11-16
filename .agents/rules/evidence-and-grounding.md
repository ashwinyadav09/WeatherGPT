---
trigger: always_on
description: Every user-visible number comes from an evidence packet and is verified before delivery.
---

# Evidence and grounding

- Source every number from an evidence packet (source, authority tier, issue time, validity window, place, units, uncertainty, attribution).
- Run the grounding verifier on every answer. On failure, regenerate once, then answer from a template built directly from the evidence.
- Show source and issue time whenever the user asks where an answer comes from.
- When an official forecast and model guidance disagree materially, show both and label each.
- Say plainly when a source is stale or down, and name the fallback used.
- Name the source that actually answered (for example Open-Meteo or IMD), and say so when an official IMD forecast is not connected.
- Express uncertainty with the project's phrase map per language; prefer IMD's own categories over invented ones.
