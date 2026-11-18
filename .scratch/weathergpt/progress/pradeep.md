# Ledger: pradeep

Edit only this file. Rows: | ticket | title | status | notes |. Statuses: todo, in-progress, in-review, blocked, done.

| Ticket | Title | Status | Notes |
|---|---|---|---|
| 01c | Web shell | done | Merged to main |
| 03 | Places real people say | done | Merged to main |
| 20 | Website experience (PWA, offline, data saver, sharing, privacy) | done | Merged to main |
| 06 | Voice v1 (Hindi) | done | Merged to main |
| 10 | Advisories v1 (guidance cards) | done | Merged to main |
| 11 | Language waves 2 and 3 | done | Merged to main |
| 19 | Agromet and marine advisories (after the IMD key arrives) | done | Merged to main |
| 14 | Aviation and smart-city read-only modules | done | Merged to main |

## Assumptions

- Mock API server and client fallback provide local contract responses for offline development and testing.
- Local places database provides offline resolution for over 200 Indian locations; falls back to Open-Meteo geocoding if online.

## Human-only steps open

- Native-speaker sign-off for Hindi UI text in seeds/i18n and apps/web/src/i18n/locales/hi.json.
- Native-speaker sign-off for Marathi, Bengali, Telugu, and Tamil text in seeds/i18n and alert templates.
- Domain reviewer sign-off for agromet advisory guidance content and marine bulletin formats.
