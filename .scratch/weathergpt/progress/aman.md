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
| R11 | Bias correction (post-processing of NWP) | done | Merged in PR #78 |

## Assumptions

- R11: Downloaded real ECMWF IFS, GFS, and ICON previous runs from Open-Meteo for 12 airport stations across India paired with real IEM ASOS METAR hourly observations (QC filtered: -5 to 55°C, >=16 obs/day, day & night coverage) and precipitation reanalysis proxy truth; enforced chronological split with 7-day embargo buffer (train: 2023-06-01 to 2024-04-23, test: 2024-05-01 to 2024-10-31 including full June-Sept monsoon); trained temperature Ridge MOS and Quantile Regression (p10, p50, p90) plus rain logistic occurrence model; evaluated on 5,601 test samples with paired block bootstrap (B=2000, fixed seed 42) showing MAE improvement of -0.086°C (95% CI [-0.139, -0.030]) excluding zero, passing production gate; integrated ForecastService post-hook applying correction within 100 km and 300 m elevation of training stations when ml_mode=ml.
- R10: Created requirements-ml.txt with lazy ML import strategy; created ml/common/manifest.py raising on HTTP errors and never returning fallback data; created ml/common/splits.py with chronological order and 7-day embargo buffer + rolling-origin folds; created ml/common/stats.py with MAE, RMSE, bias, Brier, BSS, HSS, PR-AUC, ECE, and paired weekly block bootstrap (B=2000, fixed seed); created ml/common/report.py rendering MODEL_CARD.md strictly failing on missing values; covered all functions with hand-calculated unit tests in test_ml_common.py.
- Operating with IMD key pending (ADR 0007).
- Selected Telegram Bot API for extra channel due to zero marginal cost, privacy compliance, and avoidance of commercial TRAI DLT registration.

## Human-only steps open

- Native-speaker sign-off for Hindi alert templates in seeds/i18n/alert-templates.yaml.
