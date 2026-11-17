# Ledger: pradeep

Edit only this file. Rows: | ticket | title | status | notes |. Statuses: todo, in-progress, in-review, blocked, done.

| Ticket | Title | Status | Notes |
|---|---|---|---|
| 01c | Web shell | in-review | Web shell completed, CI green, PR body in .scratch/weathergpt/pr/ticket-01c-web-shell.md |
| 03 | Places real people say | in-review | LocationResolver completed, 99.5% district / 100% panchayat accuracy on 298 cases, PR body in .scratch/weathergpt/pr/ticket-03-places-real-people-say.md |
| 20 | Website experience (PWA, offline, data saver, sharing, privacy) | todo | |
| 06 | Voice v1 (Hindi) | todo | |
| 10 | Advisories v1 (guidance cards) | todo | |
| 11 | Language waves 2 and 3 | todo | |
| 19 | Agromet and marine advisories (after the IMD key arrives) | waits for the IMD key | |
| 14 | Aviation and smart-city read-only modules | todo | |

## Assumptions

- Mock API server and client fallback provide local contract responses for offline development and testing.
- Local places database provides offline resolution for over 200 Indian locations; falls back to Open-Meteo geocoding if online.

## Human-only steps open

- Native-speaker sign-off for Hindi UI text in seeds/i18n and apps/web/src/i18n/locales/hi.json.
- Open PR for ticket/01c-web-shell on GitHub when gh CLI / remote access is available.
- Open PR for ticket/03-places-real-people-say on GitHub when gh CLI / remote access is available.
