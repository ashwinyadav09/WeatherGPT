# Ledger: aman

Edit only this file. Rows: | ticket | title | status | notes |. Statuses: todo, in-progress, in-review, blocked, done.

| Ticket | Title | Status | Notes |
|---|---|---|---|
| 01b | Fixtures and spikes | in-review | PR body saved to .scratch/weathergpt/pr/ticket-01b-fixtures-and-spikes.md; human-only: open PR on GitHub (gh not installed) |
| 05 | Alerts v1 | todo | |
| 07 | Model plane | todo | |
| 08 | Real-time integration showcase | todo | |
| 09 | Climate questions | todo | |
| 15 | Intent and slot model (optional ML training) | todo | |
| 16 | Point-forecast bias correction (optional ML training) | todo | |
| 13 | Extra channels (after a cost check) | todo | |

## Assumptions

- Bhashini key not yet approved; no Bhashini fixtures in 01b.
- Open-Meteo pune_forecast.json (original documented-sample) preserved to keep existing seam test; 11 live city forecasts in separate files.
- IEM temperatures are Fahrenheit — adapters must convert.
- IMD colour-code inversion documented in NOTES.md; adapters to normalize.

## Human-only steps open

- **01b**: Open pull request on GitHub at https://github.com/ashwinyadav09/WeatherGPT/pull/new/ticket/01b-fixtures-and-spikes (gh CLI not installed). PR body is at .scratch/weathergpt/pr/ticket-01b-fixtures-and-spikes.md. Reviewer: ashwin.
