# 0011: IMD is out of scope for this pilot

**Status:** accepted (22 November 2026)

**Context:** ADR 0007 placed IMD adapters behind a flag while a key was pending. The key has not arrived and the team has decided not to depend on it. Requiring IMD caused misleading "IMD not connected" messages in the UI and test expectations that checked for that string rather than the data.

**Decision:** IMD is not a dependency of this pilot. Its adapters remain in the repository behind the existing `IMD_ENABLED` flag (ADR 0007) but are dormant. No ticket, test, UI string, golden expectation or report may require IMD or test for the absence of an IMD connection. The primary forecast source is Open-Meteo (global model, CC BY 4.0); answers name that source. The primary alert source is NDMA SACHET. Tickets 17, 18 and 19 from the original plan are parked with the note "parked: IMD out of scope". The rule file `.agents/rules/no-simulated-results.md` rule 8 enforces this.

**Consequences:** No "IMD not connected" strings in user-visible text or golden tests. The forecast source attribution reads "Open-Meteo (global model), issued <time>". IMD adapters compile and are covered by dormant tests but are never activated in default configuration.
