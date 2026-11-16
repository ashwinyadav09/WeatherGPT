# 17: IMD forecasts live (after the IMD key arrives)

**What to build:** The IMD city forecast and panchayat forecast adapters, built earlier against IMD's documented samples, are verified against live responses and switched on, so answers cite IMD as the official forecast and rank it above model data on the authority ladder.

**Blocked by:** 02, 03 (and the IMD key, a human step)

**Owner:** ashwin | **Reviewer:** aman

**Status:** ready-for-agent once team/status.md says imd_key_available: yes

- [ ] Live fixtures are recorded and dated, and every difference from the documented samples is listed and handled in the parsers
- [ ] The conformance suite passes on live-recorded fixtures for the city forecast and panchayat forecast adapters
- [ ] The IMD flag is on in development; answers name IMD with issue time and validity, and show disagreement with model data
- [ ] The panchayat forecast is shown with its source and issue time for places that have one
- [ ] IMD rate limits and error responses are handled with backoff and a clear user message
- [ ] The golden sets still pass and the licence register entry for IMD is complete
