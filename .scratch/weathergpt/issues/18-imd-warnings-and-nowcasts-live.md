# 18: IMD warnings and nowcasts live (after the IMD key arrives)

**What to build:** IMD's district warnings, sub-division warnings and district and station nowcasts join the alert pipeline and the answers alongside SACHET, with every colour code and time field mapped explicitly.

**Blocked by:** 05, 17

**Owner:** ashwin | **Reviewer:** aman

**Status:** ready-for-agent once team/status.md says imd_key_available: yes

- [ ] Live fixtures are recorded and dated for the warning and nowcast endpoints
- [ ] Colour codes are mapped explicitly per endpoint (the nowcast and district warning endpoints use opposite orders), with a test for each mapping against live-recorded fixtures
- [ ] Times in UTC, IST and HHmm are parsed with explicit rules and tested
- [ ] An IMD warning and a SACHET alert for the same event merge into one alert, not two
- [ ] The alert-path test still asserts that no LLM call occurs between ingest and push
- [ ] Replay latency stays at or under 60 seconds at p95 from receipt to push
