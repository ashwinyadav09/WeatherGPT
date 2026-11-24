# WeatherGPT Evaluation & Acceptance Results

- **Date**: 2026-11-25
- **Status**: Acceptance tracking across 19 gates

---

## 1. End-to-End Accuracy across Tier-1 Languages

Evaluated against intent-structured golden sets across 11 Indian cities over recorded Open-Meteo fixtures:

| Language | Code | Total Cases | Passed | Accuracy (%) | Target | Status | Note |
|---|---|---|---|---|---|---|---|
| English | `en` | 48 | 48 | 100.0% | >= 95.0% | Pass (Fixture) | Template-built cases over fixture data, not a product measurement |
| Hindi | `hi` | 318 | 318 | 100.0% | >= 95.0% | Pass (Fixture) | Template-built cases over fixture data, not a product measurement |
| Bengali | `bn` | 318 | 317 | 99.7% | >= 95.0% | Pass (Fixture) | Template-built cases over fixture data, not a product measurement |
| Marathi | `mr` | 318 | 316 | 99.4% | >= 95.0% | Pass (Fixture) | Template-built cases over fixture data, not a product measurement |
| Telugu | `te` | 318 | 310 | 97.5% | >= 95.0% | Pass (Fixture) | Template-built cases over fixture data, not a product measurement |
| Tamil | `ta` | 318 | 318 | 100.0% | >= 95.0% | Pass (Fixture) | Template-built cases over fixture data, not a product measurement |
| Odia | `or` | 18 | 18 | 100.0% | >= 95.0% | Pass (Fixture) | Template-built cases over fixture data, not a product measurement |

*Note: Real city recordings and live evaluations are scheduled in tickets R20.3 and R20.12.*

---

## 2. Response Latency & TTFT

- **Time to First Token (TTFT)**: `NOT MEASURED` (undergoing live stack evaluation in R20.12).
- **Total Duration**: `NOT MEASURED` (undergoing live stack evaluation in R20.12).

---

## 3. Concurrency & Scalability Load Testing

- **20 Concurrent Users**: `NOT MEASURED` (undergoing live HTTP stack testing in R20.12).
- **50 Concurrent Users**: `NOT MEASURED` (undergoing live HTTP stack testing in R20.12).
- **100 Concurrent Users**: `NOT MEASURED` (undergoing live HTTP stack testing in R20.12).

---

## 4. Accessibility Audit (WCAG 2.2 AA)

- **Automated Scan**: `@axe-core/playwright` v4.9.1 checking WCAG 2.2 Level AA rules across 5 core views (`/`, `/#alerts`, `/#places`, `/#more`, `/offline.html`).
- **Violations**: **0 critical, 0 serious, 0 moderate, 0 minor** (Pass).
- **Manual Screen Readers**: NVDA (Windows) and TalkBack (Android) marked **`NOT MEASURED`** (requires human operator on physical hardware).

---

## 5. Speech ASR Evaluation (7 Tier-1 Languages)

Evaluated on >= 20 field/consented weather speech utterances per language:

| Language | Code | Utterance Count | Word Error Rate (WER) | Place Error Rate (PNER) | Number Error Rate (NER) | Status |
|---|---|---|---|---|---|---|
| English | `en` | 25 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED (pending H3 audio) |
| Hindi | `hi` | 110 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED (pending H3 audio) |
| Bengali | `bn` | 25 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED (pending H3 audio) |
| Marathi | `mr` | 25 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED (pending H3 audio) |
| Telugu | `te` | 25 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED (pending H3 audio) |
| Tamil | `ta` | 25 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED (pending H3 audio) |
| Odia | `or` | 25 | NOT MEASURED | NOT MEASURED | NOT MEASURED | NOT MEASURED (pending H3 audio) |

- **Speech Status**: `NOT MEASURED` (Real recorded audio pending human task H3 per Rule T2 / S1).

---

## 6. Five Core Ablation Studies

- **Ablation 1 (Tools vs No Tools)**: `NOT MEASURED` (scheduled for re-evaluation in R20.11).
- **Ablation 2 (Tools vs Tools + RAG)**: `NOT MEASURED` (scheduled for re-evaluation in R20.11).
- **Ablation 3 (Raw NWP vs Ridge vs LightGBM)**: `NOT MEASURED` (scheduled for re-evaluation in R20.11 from R20.6 predictions).
- **Ablation 4 (Encoder vs LLM Intent)**: `NOT MEASURED` (scheduled for re-evaluation in R20.11 from R20.7 predictions).
- **Ablation 5 (Cascaded vs Native Generation)**: `NOT MEASURED` (scheduled for re-evaluation in R20.11).

---

## 7. Data Provenance & Reproducibility

- **Golden Sets**: 11 recorded city fixtures from Open-Meteo (`eval/fixtures/open_meteo/`).
- **Advisories & Knowledge**: Public NDMA guidelines and ICAR crop alerts recorded in `seeds/knowledge/sources.csv`.
- **Alert Feeds**: Real NDMA SACHET CAP fixtures (`eval/fixtures/sachet/`); live 48h poller alert freshness is `NOT MEASURED` (< 5 live alerts observed).
- **LLM Judge Calibration**: `NOT MEASURED` pending independent human scoring H4.
