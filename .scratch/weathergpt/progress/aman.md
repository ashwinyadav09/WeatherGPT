# Ledger: aman

Edit only this file. Rows: | ticket | title | status | notes |. Statuses: todo, in-progress, in-review, blocked, done.

| Ticket | Title | Status | Notes |
|---|---|---|---|
| 01b | Fixtures and spikes | done | Merged in PR #40 |
| 05 | Alerts v1 | done | Merged in PR #40 |
| 07 | Model plane | done | Merged in PR #35 |
| 08 | Real-time integration showcase | done | Merged in PR #36 |
| 09 | Climate questions | done | Merged in PR #37 |
| 15 | Intent and slot model (optional ML training) | done | Merged in PR #38 |
| 16 | Point-forecast bias correction (optional ML training) | done | Merged in PR #39 |
| 13 | Extra channels (after a cost check) | done | Merged in PR #40; CI fix in PR #51 |
| R10 | ML foundation | done | Merged in PR #77 |

## Assumptions

- R10: Created requirements-ml.txt with lazy ML import strategy; created ml/common/manifest.py raising on HTTP errors and never returning fallback data; created ml/common/splits.py with chronological order and 7-day embargo buffer + rolling-origin folds; created ml/common/stats.py with MAE, RMSE, bias, Brier, BSS, HSS, PR-AUC, ECE, and paired weekly block bootstrap (B=2000, fixed seed); created ml/common/report.py rendering MODEL_CARD.md strictly failing on missing values; covered all functions with hand-calculated unit tests in test_ml_common.py.
- Operating with IMD key pending (ADR 0007).
- Selected Telegram Bot API for extra channel due to zero marginal cost, privacy compliance, and avoidance of commercial TRAI DLT registration.

## Human-only steps open

- Native-speaker sign-off for Hindi alert templates in seeds/i18n/alert-templates.yaml.
