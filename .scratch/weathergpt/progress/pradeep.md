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
| R13 | Climate trend and anomaly | done | Implemented ERA5 reanalysis pipeline, WMO 1991-2020 normals, Mann-Kendall Sen slope with LOO stability, and Isolation Forest |
| R17 | Visible AI and ML in the web app | done | TracePanel in AnswerCard, ML Lab feature with 5 model tabs, all 7 Tier-1 locales and Indic fonts |

## Assumptions

- Mock API server and client fallback provide local contract responses for offline development and testing.
- Local places database provides offline resolution for over 200 Indian locations; falls back to Open-Meteo geocoding if online.
- R17: Built TracePanel in AnswerCard displaying intent, confidence, router path, tools and sources, raw vs corrected temperature with p10-p90 band, risk with SHAP drivers, retrieved RAG passages with IDs, grounding verifier status, and LLM metrics; implemented ML Lab feature under apps/web/src/features/ml-lab/ with tabs for all 5 models and overall eval summary, pulling data strictly from /v1/ml/* with NOT MEASURED for missing values, plus interactive Try It live inference; deployed all 7 Tier-1 locales (en, hi, bn, mr, te, ta, or) and Indic Google fonts in web app; updated accessibility spec to verify axe accessibility across all seven Tier-1 languages.

## Human-only steps open

- Native-speaker sign-off for Hindi UI text in seeds/i18n and apps/web/src/i18n/locales/hi.json.
- Native-speaker sign-off for Marathi, Bengali, Telugu, and Tamil text in seeds/i18n and alert templates.
- Domain reviewer sign-off for agromet advisory guidance content and marine bulletin formats.
