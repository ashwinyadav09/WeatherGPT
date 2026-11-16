# 0001: Relay official alerts; never write them

**Status:** accepted (6 November 2026)

**Context:** Section 54 of the Disaster Management Act punishes making or circulating a false alarm about a disaster, and state authorities have urged the public to rely on IMD and state disaster authorities. LLMs can embellish.

**Decision:** WeatherGPT shows official alerts as issued, from SACHET and the IMD APIs, through vetted templates. No LLM call sits in the alert path. Model-derived heads-ups stay out of the pilot.

**Consequences:** Alerts are never wider or earlier than the official ones. Alert text needs human-vetted templates per language. A production route may need a dissemination-partner arrangement with NDMA or C-DOT.
