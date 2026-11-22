# Ledger: ashwin

Edit only this file. Rows: | ticket | title | status | notes |. Statuses: todo, in-progress, in-review, blocked, done.

| Ticket | Title | Status | Notes |
|---|---|---|---|
| 01a | Platform skeleton | done | Merged in PR #25 |
| 02 | Will it rain tomorrow? | done | Merged in PR #26 |
| 04 | Hindi text | done | Merged in PR #29 |
| 21 | Admin console | done | Merged in PR #30 |
| 17 | IMD forecasts live | parked | parked: IMD out of scope (ADR 0011) |
| 18 | IMD warnings and nowcasts live | parked | parked: IMD out of scope (ADR 0011) |
| 12 | Hardening | done | Merged in PR #31 |
| 22 | Demo, docs and deployment pack | done | Merged in PR #32 |
| R0.1 | Install truthfulness rules | done | Merged in PR #52 |
| R0.2 | Quarantine unverified artifacts and fix gates | done | Merged in PR #53 |
| R0.3 | Fix agent correctness | in-review | branch ticket/R0.3-fix-agent-correctness; 162 tests pass, CI green; tomorrow uses day index 1, defaults removed |
| R0.4 | Remove IMD coupling and fixture-as-official | todo | |
| R0.5 | Speech: Sarvam primary, no canned transcripts | todo | |

## Assumptions

- R0.1: ADR numbers 0010/0011/0012 (0008 and 0009 already existed in repo for other decisions).
- R0.2: archive directory path is `docs/archive/unverified/`.
- R0.3: per-day packets have valid_from/to matching local midnight intervals with day index steps.

## Human-only steps open

- Native-speaker sign-off on Hindi glossary and templates (#28)
