# 14: Aviation and smart-city read-only modules

**What to build:** A pilot can ask for an aerodrome's METAR and TAF and see them decoded beside the raw text, with flight category and crosswind. A city operator can subscribe to threshold alerts (heat index, lightning, rain intensity) delivered by webhook.

**Blocked by:** 07

**Owner:** pradeep | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] METAR and TAF decode with the raw text alongside and an informational banner that this is not a briefing
- [ ] Crosswind and flight category are computed in code and match hand-checked worked examples
- [ ] AviationWeather.gov limits are respected through caching
- [ ] Threshold subscriptions deliver webhooks with rate limits and delivery logs
