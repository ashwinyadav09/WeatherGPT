# 0007: IMD adapters behind a flag while the key is pending

**Status:** accepted (14 November 2026)

**Context:** The IMD API key was applied for and approval takes time. IMD is the official forecast source, but the build should not stop.

**Decision:** IMD adapters are built contract-first against the example responses in IMD's published API reference and stay behind a flag. Until the key arrives, Open-Meteo is the first forecast source (aggregator tier), SACHET carries IMD's warnings, and global model ingest follows. Every answer names its real source and says when an official IMD forecast is not connected. Fixtures carry a provenance label, and an IMD adapter counts as verified only after live-recorded fixtures pass its conformance suite (tickets 17 to 19).

**Consequences:** Work continues without the key. Early answers are model data, not official forecasts, and say so. Some IMD field details may differ from the documented samples; ticket 17 finds and fixes them.
