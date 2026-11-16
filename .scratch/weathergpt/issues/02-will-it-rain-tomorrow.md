# 02: Will it rain tomorrow?

**What to build:** A user opens the website, types "Will it rain tomorrow in Pune?" and gets a short answer card with the key number, an icon, the source, the issue time and the validity. The number is checked against its evidence packet before it is shown. The ticket also produces a latency report for the text path.

**Blocked by:** 01a, 01b, 01c

**Owner:** ashwin | **Reviewer:** pradeep

**Status:** ready-for-agent

- [ ] The Conversation API answers through a ForecastService with an Open-Meteo adapter switched on first; an IMD city-forecast adapter is built against documented samples and stays off behind a flag until the IMD key arrives
- [ ] The answer card shows headline, number, icon, source and issue time
- [ ] The card names the real source (Open-Meteo for now) and says when an official IMD forecast is not connected
- [ ] The grounding verifier blocks an answer whose number differs from the evidence and falls back to a templated answer (adversarial case in tests)
- [ ] All model calls go through the LLM gateway, with a stub and an OpenAI-compatible adapter configured for OpenRouter or Groq
- [ ] A golden set of at least 30 English cases for this question type passes
- [ ] A latency report gives p50 and p95 for the text path against the design budget
- [ ] Works in current Chrome and Firefox on desktop and in a phone-sized viewport
- [ ] The Ask page and answer card are built in the web shell's Ask feature following docs/ui-spec.md, replacing the placeholder
- [ ] Place resolution uses the minimal geocoding adapter from ticket 01a; ticket 03 replaces it with the full resolver
- [ ] Model IDs are read from config/models.yaml or the environment; tests use the stub, and demos use a tool-calling model from the provider keys in .env
