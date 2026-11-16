# WeatherGPT spec

## Problem Statement

Weather information in India is spread across IMD portals and APIs, national alert feeds, global model data, marine and aviation sources and climate archives, in formats and languages that most people cannot use quickly. A farmer who wants to know whether to irrigate tomorrow, a villager who needs to know what an orange warning means for her village, or a researcher who wants a rainfall anomaly must visit several places, read English bulletins or raw numbers, and judge for themselves how current and trustworthy each source is. Existing helpers cover pieces (village forecasts, alerts, one-way SMS, scheme chatbots), but none offers one conversational, voice-first, multilingual assistant that is grounded in official data and careful about warnings.

## Solution

WeatherGPT is a free, non-commercial website (installable on a phone as a progressive web app) where people ask about weather by voice or text in their own language and get a short, grounded answer: the key number, an icon, the source and the issue time. It resolves places down to the gram panchayat, shows official alerts for the user's places in their language exactly as issued, gives advisories drawn from official guidance, answers climate and history questions with named datasets, and explains uncertainty in plain words. It uses official Indian data first and independent global models as backup and cross-check. The language model understands and explains; it never supplies facts and never writes warnings.

## User Stories

**Weather and forecasts**
1. As a farmer, I want to ask in Hindi whether it will rain tomorrow at my village, so that I can decide whether to irrigate or harvest.
2. As a general user, I want to see current conditions for my location with the source and time, so that I can judge how fresh they are.
3. As a general user, I want an hourly outlook for the next day and a daily outlook for ten days, so that I can plan my day and my week.
4. As a user, I want to ask follow-ups such as "and the day after?" without repeating the place, so that the conversation feels natural.
5. As a user, I want one clarifying question when a place name is ambiguous, so that I never get the wrong town's forecast.
6. As a user, I want rain chances explained in plain words, so that I understand how sure the forecast is.
7. As a user, I want to see when official and model forecasts disagree, so that I know to check again later.
8. As a user, I want to ask where an answer comes from and get the source and issue time, so that I can verify it.
9. As a user, I want an honest message when a data source is down, so that I do not rely on a stale answer.
10. As a user on a weak network, I want the last answer cached and a data-saver mode, so that the site stays useful with poor signal.

**Places**
11. As a villager, I want to say my gram panchayat or village name in my own language, so that I get a forecast for my place and not the district.
12. As a user, I want to use GPS or pick from saved places (home, farm, work), so that I can switch quickly.
13. As a user, I want Indic-script names and common transliterations to resolve to the same place, so that spelling never blocks me.

**Alerts**
14. As a person in a warned area, I want a push notification in my language when an official warning covers my place, so that I can act early.
15. As an alert recipient, I want each alert to say who issued it, when, and until when, so that I know it is official and current.
16. As an alert recipient, I want updates to replace earlier alerts and cancellations to show an all-clear, so that stale warnings do not confuse me.
17. As an alert recipient, I want severity shown by colour, icon, words and audio, so that I understand even if I cannot read well or tell colours apart.
18. As an alert recipient, I want to ask what an orange alert means for me and what official guidance says to do, so that I can take concrete steps.
19. As a user, I want to choose which severities notify me and set quiet hours (red always gets through), so that I am not overwhelmed.
20. As a user, I want to see active alerts for any place I name, not only saved ones, so that I can check on family elsewhere.
21. As the operator, I want the app never to write its own warnings, so that it cannot cause a false alarm.
22. As a user, I want to be pointed to official guidance and local authorities when I ask whether to evacuate, so that I decide with the right sources.

**Voice and language**
23. As a low-literacy user, I want to hold a button, speak and hear the answer, so that I need not read or type.
24. As a Hindi speaker who mixes in English words, I want to be understood, so that I can speak naturally.
25. As a user, I want an uncertain place name read back for confirmation, so that recognition mistakes are caught.
26. As a new user, I want to pick my language at first visit from spoken language names, so that I can start without reading.
27. As a user, I want a transcript of what I said and what the app said, with replay and slow-down, so that I can check and hear it again.
28. As a user, I want weather terms and units spoken naturally in my language, so that answers sound right.
29. As a user of a language that is not fully supported yet, I want to type or speak and get a text answer plus vetted alerts, so that I am not locked out.
30. As a team member, I want a native-speaker review gate before any new language ships, so that quality stays controlled.

**Advisories**
31. As a farmer, I want to name my crop and growth stage and get advice for the coming days based on IMD's agromet advisory, so that I can time sowing, irrigation and spraying.
32. As a farmer, I want advice that names its source and never gives pesticide doses, so that I rely on safe, official guidance.
33. As a coastal fisher, I want sea and coastal bulletins and fishermen warnings in my language, so that I know whether it is safe to go out.
34. As an urban resident, I want heat and cold-wave guidance when official warnings apply, so that I can protect my family.

**Climate and history**
35. As a curious user or researcher, I want to ask how this month's rainfall compares with the long-term normal for my district, so that I understand anomalies.
36. As a user, I want percentiles, counts of days above a threshold and simple trends with caveats, so that I interpret climate correctly.
37. As a researcher, I want each climate answer to name its dataset, period and resolution, so that I can cite it.
38. As a researcher, I want to export the data behind an answer (later phase), so that I can reuse it.

**Aviation, cities and disaster managers (later phases)**
39. As a general aviation pilot, I want decoded METAR and TAF for an aerodrome with the raw text beside them, so that I get situational awareness (not a briefing).
40. As a pilot, I want crosswind computed correctly and the flight category shown, so that I can read conditions quickly.
41. As a smart-city operator, I want threshold subscriptions with webhooks, so that my dashboards react to heat, lightning or rain.
42. As a disaster manager, I want a district summary of active official warnings, so that I can brief teams.

**Trust, privacy and accessibility**
43. As a user, I want a consent notice in my language explaining how location and voice are used, so that I can decide knowingly.
44. As a user, I want to delete my data from the site, so that I stay in control.
45. As a user, I want no raw audio kept by default, so that my voice is not stored.
46. As a user with a screen reader, I want every page to work with screen readers such as NVDA and TalkBack, so that the site is accessible.
47. As a user with an older phone, I want the site to run smoothly in a mobile browser on low-end Android, so that device cost is no barrier.
48. As a user, I want to share an answer as a link, image or audio clip to WhatsApp, so that family and neighbours benefit.
49. As a user, I want a licences and sources page, so that I know where data comes from and that the site is non-commercial.

**Operator and developer**
50. As the operator, I want a live status page showing source freshness, ingest completeness and alert latency, so that I can see integration health.
51. As the operator, I want automatic fallback to global model guidance when IMD's service is down, so that users still get a labelled answer.
52. As the operator, I want a golden-set evaluation per language before each release, so that quality never regresses silently.
53. As the operator, I want a replay harness for historical alerts, so that I can test alert logic safely.
54. As the operator, I want cost per 1,000 queries and per voice minute visible, so that a free service stays sustainable.
55. As the operator, I want rate limits and abuse protection, so that the service stays up during surges.
56. As an editor, I want an admin console for glossary and alert templates with an audit log, so that wording stays vetted.
57. As a developer or agent, I want a documented procedure for adding a data source, language or alert template, so that growth is repeatable.
58. As a developer or agent, I want recorded fixtures and conformance tests per adapter, so that upstream API changes are caught early.
59. As the operator, I want model providers swappable through configuration, so that vendor changes do not break the product.
60. As a user, I want answers within a few seconds, and first audio within about three and a half seconds for voice, so that the assistant feels responsive.
61. As the operator, I want a small trained model to route questions quickly, so that simple turns cost less and answer faster.
62. As a user, I want model-guidance forecasts corrected for known local errors, so that point forecasts are closer to what actually happens.

## Implementation Decisions

**Product and scope**
- A free, ad-free, non-commercial public-interest pilot. India-first, with global model guidance for questions that are neither alerts nor advisories. Pilot user testing in Uttar Pradesh and Maharashtra; the data layer covers all of India.
- Hindi and English first, then Bengali, Marathi, Tamil and Telugu, then the rest of the voice-capable set. Every new language passes a native-speaker gate.
- A responsive website that can be added to the home screen as a progressive web app. There is no native app. Other channels (WhatsApp, Telegram, IVR, SMS) wait for a cost check.
- Every source is attributed in the app and API; no ads, payments or resale of source data.

**Answering pipeline**
- The conversation service runs: understand, resolve place, plan, fetch, compose, verify, deliver. A failed verification regenerates once, then falls back to a template built directly from the evidence.
- The evidence packet is the one shape every tool returns: id, source, authority tier (1 official warning to 5 aggregator), issue time, validity window, place, values with units and step, uncertainty, attribution and fetch time.
- Sources are ranked by an authority ladder (official warning, official forecast, national model, global model, aggregator, LLM narrative). When official and model guidance disagree materially, both are shown and labelled; they are never averaged silently.
- Tools are few and deep: resolve place, current conditions, forecast, alerts, climate statistic, advisory, aviation weather, marine, explain term.
- Uncertainty uses IMD's own categories first, then a phrase map per language that is validated with users.
- Evacuation, medical and legal questions get a redirect to official guidance. Memory holds saved places, crop, language and voice, with consent and short retention; raw audio is not kept by default.

**Modules and interfaces**
- ForecastService takes a place, a window and variables, and returns evidence packets. It picks sources by the authority ladder and caches by place cell and hour. Adapters: IMD city and panchayat forecasts, IMD nowcasts, GFS point, ECMWF IFS/AIFS point, Open-Meteo.
- AlertEngine ingests official messages and matches places to alert events. Source adapters: SACHET feeds and IMD warning APIs. Disseminator adapters: Web Push first; SMS and WhatsApp later.
- LocationResolver turns text, language and hints into places, including panchayat names, Indic transliterations and GPS.
- ClimateService answers statistics for a place, variable, period and statistic.
- AdvisoryEngine returns advice packets from retrieved official guidance (rule packs come later).
- SpeechGateway handles transcription, synthesis and translation behind provider adapters. LLMGateway handles model calls behind provider adapters, with routing, retries, caching and tracing.
- GroundingVerifier checks every number and unit in an answer against its evidence.
- An admin console manages glossary and alert templates with an audit log.
- An intent and slot model (trained in ticket 15) routes each question before the LLM is called, and low-confidence turns fall back to the LLM.
- A bias-correction component (trained in ticket 16) adjusts model-guidance point forecasts where it beats the raw model on held-out data.

**Data and ingest**
- IMD products are primary for India; GFS and ECMWF IFS/AIFS are ingested as independent guidance, ensembles and fallback through one model-output contract with an adapter per source. WRF output from a partner can join through the same contract; WeatherGPT does not run WRF in the pilot.
- The IMD API key is pending, so IMD adapters sit behind a flag. Until it arrives, Open-Meteo is the first forecast source, SACHET carries IMD's warnings, and every answer names its real source and says when an official IMD forecast is not connected. IMD adapters are first built and tested against the example responses in IMD's published API reference, labelled documented-sample, then verified against live-recorded fixtures (tickets 17 to 19).
- A WIS2 subscriber feeds real-time observations and products into the status dashboard.
- Freshness targets: IMD warnings polled at least every five minutes; model fields queryable within thirty minutes of publication.

**Alerts**
- The alert source of record is SACHET's CAP feeds plus the IMD warning APIs, normalised to one alert schema. Alerts are matched to saved or current places by polygon, with district fallback.
- Official text is shown as issued, with sender, issue time and expiry. Wording comes from vetted templates keyed by hazard, severity and action, with slots only for place and time. No LLM sits in the alert path.
- IMD colour codes are mapped explicitly per endpoint, and IMD time fields are parsed with explicit rules.
- Web Push notifications come first. Model-derived heads-ups stay out of the pilot.

**Speech and language**
- Bhashini is the primary speech provider; a second provider (Sarvam) sits behind the same gateway so the seam is real. Self-hosted open models come later if volume or sovereignty requires them.
- LLM adapters at the start: one OpenAI-compatible adapter that serves OpenRouter and Groq through a base URL and a key, plus a test stub; Sarvam and Gemini adapters can follow. A main model and a fast model (for routing and short turns) are chosen by golden-set results, must support tool calling, and live in configuration.
- Browser microphone capture streams audio to the backend, which converts it to the format each speech provider needs; speech output plays in the browser.
- Recognition is biased toward place names, crops and hazard terms. Uncertain place names are read back. Speech output normalises units, degrees and times per language.
- Language tiers: A voice in and out; B voice in and text out; C text and vetted alert templates.

**Climate and advisories**
- Climate answers come from deterministic tools over IMD gridded data and normals (access terms to confirm) and ERA5, and always name dataset, period and resolution. The LLM runs no free-form code against data.
- Official heat and cold-wave guidance cards come first. After the IMD key arrives (ticket 19), the pilot advisory summarises IMD's agromet advisory for the user's district for wheat and rice, with citation, and marine bulletins are read-only. No pesticide doses. Custom rule packs come later with agronomist review.

**Platform**
- Python with FastAPI; PostgreSQL with PostGIS (full-text search for the small guidance library); Redis; Zarr on a local volume behind an S3-compatible path layer; a scheduled worker (APScheduler) for ingest; React with TypeScript and Vite, built as a progressive web app, for the website; Docker Compose on one India-region VM for the pilot, with Kubernetes manifests added at hardening. Structured JSON logs, a Prometheus metrics endpoint and the status page for observability; OpenTelemetry and Grafana can follow at hardening.
- Initial performance targets, to recalibrate after the first latency spike: text time to first token p95 at or under 1.5 seconds and full answer p95 at or under 5 seconds; voice first audio p95 at or under 3.5 seconds on 4G; alert hop from receipt to push p95 at or under 60 seconds; availability 99.9 percent for alerts and 99.5 percent for chat.

**Models and external services**
- Pretrained models do the language, speech and retrieval work, so nothing has to be trained to ship the pilot. Two small models are trained for real ML value: an intent and slot model, and a point-forecast bias correction. Each ships only if it beats its baseline on held-out data.
- Keys needed: the IMD API (pending), Bhashini and one LLM key (Groq and OpenRouter are already available); optional: Sarvam and the Copernicus climate data service. No key is needed for SACHET feeds, ECMWF open data, GFS, AviationWeather.gov or Open-Meteo's free non-commercial tier. Keys stay on the server and never reach browser code.

**Privacy and security**
- DPDP-aligned from the start: itemised consent notice in the user's language, purpose limitation, deletion on request, and an 18-plus gate subject to legal advice.
- Alert feeds only from allowlisted URLs over TLS; tool output is treated as data; a prompt-injection suite runs in CI; secrets only in environment variables or a secret manager.

## Testing Decisions

- A good test exercises external behaviour through a public interface and is red before it is green. It takes expected values from dated, recorded fixtures or hand-checked examples, never from the code under test.
- Three seams carry the tests: the Conversation API (question in, grounded answer and evidence out), the Alert pipeline (official message in, notifications out), and Adapter conformance (one reusable suite run on recorded fixtures for every external-system adapter). The GroundingVerifier is a pure function with a large input space, so it also gets property tests at its own interface; it is the only extra seam.
- Prior art: none, since the repository starts empty. Borrowed practice: recorded-fixture contract tests, golden sets per language and archetype, and a replay harness for historical alerts.
- Live APIs are touched only by scheduled contract checks, never by CI.
- Every fixture carries a provenance label (live-recorded, documented-sample or spec-only). An adapter counts as verified only when its conformance suite passes on live-recorded fixtures.
- Evaluation gates: groundedness at least 99 percent; intent and slot accuracy at least 95 percent per launch language; place resolution at least 95 percent top-1 at district level and 85 percent at panchayat level; no golden-set regression.
- Non-functional testing: load tests for concurrency and alert fan-out, a WCAG 2.2 AA accessibility audit with automated axe checks and screen readers (NVDA and TalkBack in Chrome), Playwright end-to-end tests through the browser, the prompt-injection suite, and a cost dashboard.
- Speech is tested on consented or field-like audio, measuring recognition errors on place names and numbers separately.
- Trained models are tested through the existing seams: the intent model through the Conversation API on the golden set against the LLM-only baseline, and the bias correction through forecast evaluation on time-split held-out data against the raw model.

## Out of Scope

Running WRF or training forecast models; nowcasting from radar or satellite imagery; geographies outside India beyond global-model answers; commercial use; WhatsApp, Telegram, IVR and SMS channels until a cost check passes; aviation and smart-city modules beyond read-only decoding (later tickets); on-device ML; native Android and iOS apps; custom agronomy rule packs; publishing to WIS2 as a node; legal opinions.

## Further Notes

- Decisions taken on 6 November 2026, after the product owner confirmed the product is non-commercial and delegated the rest: India-first scope; Hindi and English first; farmers, general public and alert recipients as priority users; website only, no native app; Docker Compose on one India-region VM; provider-agnostic LLM gateway; a plan-agnostic build pack; pilot restricted to languages the team can review, with no custom agronomy rules; pilot states Uttar Pradesh and Maharashtra; advisory crops wheat and rice.
- The three test seams were chosen by the spec author because the owner delegated decisions; confirm them with the owner when convenient.
- The research report behind this spec is at https://claude.ai/artifact/HBCEJJ3Px5xJ88q8ta1yPc. Its Appendix B lists 14 items not yet verified, including IMD terms for panchayat forecasts, INCOIS programmatic access and SACHET reuse terms.
- Assumes the build tool is Google Antigravity; the pack is plain Markdown and works with other agent tools.
- Which keys to get and which models to train: see the API keys guide and the ML plan in the pack's docs folder.
- IMD API access was applied for and is pending as of 14 November 2026. The build order in the issues folder works around it, and tickets 17 to 19 switch IMD on once the key arrives.
- Three people build the project through GitHub (Ashwin, Aman, Pradeep), each with their own AI agent; lanes, ownership and workflow are in docs/team.md and team/assignments.csv.
