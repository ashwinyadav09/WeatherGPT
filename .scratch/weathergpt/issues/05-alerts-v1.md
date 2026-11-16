# 05: Alerts v1

**What to build:** When an official warning from SACHET (which carries IMD, CWC, INCOIS and state alerts) covers one of a user's places, the user's browser shows a push notification in their language, and the alert centre shows the alert with sender, issue time and expiry. Updates replace earlier alerts and cancellations show an all-clear. No LLM touches any of this.

**Blocked by:** 01a, 01b, 01c

**Owner:** aman | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] SACHET feeds are ingested and normalised to one alert schema through a source adapter; IMD's own warning APIs join in ticket 18
- [ ] CAP severity, urgency and certainty are mapped explicitly to alert levels, with a test for each mapping
- [ ] Alerts are matched to saved places by polygon, with district fallback; border cases are covered
- [ ] Update and Cancel are handled; Test and Exercise messages are ignored in production and logged
- [ ] Web Push reaches test browsers (desktop and Android Chrome); the alert centre shows official alerts labelled with source and times
- [ ] Hindi and English templates are built from official wording; a back-translation check and a native-speaker sign-off are recorded (human step)
- [ ] The alerts feature folder in the web app (alert centre and notification opt-in) follows docs/ui-spec.md; saved places come from the minimal table until ticket 03 lands
- [ ] A test asserts that no LLM call occurs between ingest and push
- [ ] A replay of at least 10 recorded real alerts, including a cyclone event, reports hop timestamps with p95 from receipt to push at or under 60 seconds
