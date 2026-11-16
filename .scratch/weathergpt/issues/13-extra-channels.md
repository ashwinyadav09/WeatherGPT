# 13: Extra channels (after a cost check)

**What to build:** If a cost check shows a free or affordable route, users can reach WeatherGPT and its alerts through one more channel (WhatsApp, Telegram, IVR or SMS) with the same grounded answers and relay-only alerts.

**Blocked by:** 05

**Owner:** aman | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] A written cost and terms check compares the channels and picks one, or records that none is affordable
- [ ] The chosen channel is a disseminator or conversation adapter that passes the same conformance suite
- [ ] Consent is collected in the channel and opt-out works
- [ ] An end-to-end test covers a question, an answer and an alert
