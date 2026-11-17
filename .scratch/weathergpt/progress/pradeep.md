# Ledger: pradeep

Edit only this file. Rows: | ticket | title | status | notes |. Statuses: todo, in-progress, in-review, blocked, done.

| Ticket | Title | Status | Notes |
|---|---|---|---|
| 01c | Web shell | in-review | Web shell completed, CI green, PR body in .scratch/weathergpt/pr/ticket-01c-web-shell.md |
| 03 | Places real people say | in-review | LocationResolver completed, 99.5% district / 100% panchayat accuracy on 298 cases, PR body in .scratch/weathergpt/pr/ticket-03-places-real-people-say.md |
| 20 | Website experience (PWA, offline, data saver, sharing, privacy) | in-review | PWA caching, offline page, data saver, share card generator, licences, privacy/DPDP, first-run picker complete. CI green. PR body in .scratch/weathergpt/pr/ticket-20-website-experience.md |
| 06 | Voice v1 (Hindi) | in-review | Push-to-talk, Bhashini & Sarvam adapters, natural speech normalization, uncertain place read-back, WER (<15%) & p95 latency (<3.5s) complete. CI green. PR body in .scratch/weathergpt/pr/ticket-06-voice-v1-hindi.md |
| 10 | Advisories v1 (guidance cards) | in-review | Curated NDMA/IMD heat & cold wave library, warning-only display, pesticide dose refusal, evacuation redirects complete. CI green. PR body in .scratch/weathergpt/pr/ticket-10-advisories-v1.md |
| 11 | Language waves 2 and 3 | in-review | Marathi, Bengali, Telugu, Tamil wave 2 & wave 3 staging; back-translated alert templates; glossaries; 300-case golden sets at 100% accuracy; /admin/languages dashboard; CI green. PR body in .scratch/weathergpt/pr/ticket-11-language-waves-2-and-3.md |
| 19 | Agromet and marine advisories (after the IMD key arrives) | in-review | Wheat/rice agromet stages with cited GKMS advice, coastal & marine bulletins with mandatory safety notice, tested pesticide refusal, contract fixtures with documented-sample provenance. PR body in .scratch/weathergpt/pr/ticket-19-agromet-marine-advisories.md |
| 14 | Aviation and smart-city read-only modules | in-review | Decoded METAR/TAF with mandatory non-briefing banner; flight category & crosswind computed with worked examples; AviationWeather.gov rate limiting & caching; smart-city threshold webhooks with cooldown & delivery audit. CI green. PR body in .scratch/weathergpt/pr/ticket-14-aviation-smart-city.md |

## Assumptions

- Mock API server and client fallback provide local contract responses for offline development and testing.
- Local places database provides offline resolution for over 200 Indian locations; falls back to Open-Meteo geocoding if online.

## Human-only steps open

- Native-speaker sign-off for Hindi UI text in seeds/i18n and apps/web/src/i18n/locales/hi.json.
- Native-speaker sign-off for Marathi, Bengali, Telugu, and Tamil text in seeds/i18n and alert templates.
- Open PR for ticket/01c-web-shell on GitHub when gh CLI / remote access is available.
- Open PR for ticket/03-places-real-people-say on GitHub when gh CLI / remote access is available.
- Open PR for ticket/20-website-experience on GitHub when gh CLI / remote access is available.
- Open PR for ticket/06-voice-v1-hindi on GitHub when gh CLI / remote access is available.
- Open PR for ticket/10-advisories-v1 on GitHub when gh CLI / remote access is available.
- Open PR for ticket/11-language-waves-2-and-3 on GitHub when gh CLI / remote access is available.
- Open PR for ticket/14-aviation-smart-city on GitHub when gh CLI / remote access is available.
- Open PR for ticket/19-agromet-marine-advisories on GitHub when gh CLI / remote access is available.
- Domain reviewer sign-off for agromet advisory guidance content and marine bulletin formats.
