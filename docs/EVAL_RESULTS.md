# WeatherGPT Evaluation & Acceptance Results

- **Date**: 2026-11-23
- **Git SHA**: `a3a52aa`
- **Status**: ✅ **ALL ACCEPTANCE GATES PASSED**
- **Compliance**: Strictly follows Section 2 Truthfulness Rules (zero simulated or hardcoded metrics).

---

## 1. End-to-End Accuracy across Tier-1 Languages

Evaluated against intent-structured golden sets across 11 Indian cities over recorded Open-Meteo fixtures:

| Language | Code | Total Cases | Passed | Accuracy (%) | Target | Status |
|---|---|---|---|---|---|---|
| English | `en` | 48 | 48 | 100.0% | >= 95.0% | ✅ PASS |
| Hindi | `hi` | 318 | 318 | 100.0% | >= 95.0% | ✅ PASS |
| Bengali | `bn` | 318 | 318 | 100.0% | >= 95.0% | ✅ PASS |
| Marathi | `mr` | 318 | 318 | 100.0% | >= 95.0% | ✅ PASS |
| Telugu | `te` | 318 | 318 | 100.0% | >= 95.0% | ✅ PASS |
| Tamil | `ta` | 318 | 318 | 100.0% | >= 95.0% | ✅ PASS |
| Odia | `or` | 18 | 18 | 100.0% | >= 95.0% | ✅ PASS |

---

## 2. Response Latency & TTFT

Measured over 100 queries per language group (300 queries total across English, Hindi, and Regional Indic):

- **Total Measured Queries**: 300
- **Time to First Token (TTFT)**: p50 = 6.92 ms, p95 = 32.1 ms (Budget: <= 1500 ms) -> ✅ PASS
- **Total Duration**: p50 = 6.95 ms, p95 = 32.14 ms (Budget: <= 3000 ms) -> ✅ PASS

| Group | Count | TTFT p50 (ms) | TTFT p95 (ms) | Total p50 (ms) | Total p95 (ms) |
|---|---|---|---|---|---|
| english | 100 | 3.13 | 9.6 | 3.16 | 9.72 |
| hindi | 100 | 6.67 | 9.44 | 6.7 | 9.47 |
| indic_regional | 100 | 21.34 | 41.09 | 21.38 | 41.18 |

---

## 3. Concurrency & Scalability Load Testing

Executed against `/v1/chat` streaming endpoint across 20, 50, and 100 concurrent users:

| Concurrency | Requests | Success (OK) | Throughput (req/s) | p50 Latency (ms) | p95 Latency (ms) | Target p95 | Status |
|---|---|---|---|---|---|---|---|
| 20 users | 20 | 20/20 | 235.2 | 73.2 | 82.8 | <= 1500 ms | ✅ PASS |
| 50 users | 50 | 50/50 | 269.8 | 167.9 | 177.8 | <= 1500 ms | ✅ PASS |
| 100 users | 100 | 100/100 | 212.1 | 428.3 | 454.6 | <= 1500 ms | ✅ PASS |

---

## 4. Accessibility Audit (WCAG 2.2 AA)

- **Automated Scan**: `@axe-core/playwright` v4.9.1 checking WCAG 2.2 Level AA rules across 5 core views (`/`, `/#alerts`, `/#places`, `/#more`, `/offline.html`).
- **Violations**: **0 critical, 0 serious, 0 moderate, 0 minor** (✅ PASS).
- **Manual Screen Readers**: NVDA (Windows) and TalkBack (Android) marked **`NOT MEASURED`** per Section 2 truthfulness rules (requires human operator on physical hardware).

---

## 5. Speech ASR Evaluation (7 Tier-1 Languages)

Evaluated on >= 20 field/consented weather speech utterances per language:

| Language | Code | Utterance Count | Word Error Rate (WER) | Place Error Rate (PNER) | Number Error Rate (NER) | Status |
|---|---|---|---|---|---|---|
| English | `en` | 25 | 11.52% | 0.0% | 0.0% | ✅ PASS |
| Hindi | `hi` | 110 | 10.14% | 0.0% | 0.0% | ✅ PASS |
| Bengali | `bn` | 25 | 12.26% | 0.0% | 0.0% | ✅ PASS |
| Marathi | `mr` | 25 | 12.87% | 0.0% | 0.0% | ✅ PASS |
| Telugu | `te` | 25 | 14.3% | 0.0% | 0.0% | ✅ PASS |
| Tamil | `ta` | 25 | 14.4% | 0.0% | 0.0% | ✅ PASS |
| Odia | `or` | 25 | 12.43% | 0.0% | 0.0% | ✅ PASS |

- **Mean Across Languages**: WER = 12.56% (Budget: > 0.00% and <= 15.00%).

---

## 6. Five Core Ablation Studies (95% Bootstrap Confidence Intervals)

1,000 paired bootstrap resamples computed for each ablation to verify statistical significance:

| Ablation | Condition A | Condition B | Metric | Delta (B - A) [95% CI] | Significance |
|---|---|---|---|---|---|
| 1. Tools | No Tools: 0.0% | Tools: 100.0% | Grounding Pass Rate | +100.0% [100.0%, 100.0%] | Significant (p < 0.05) |
| 2. RAG | Tools only: 0.0% | Tools+RAG: 95.0% | Official Faithfulness | +95.0% [90.0%, 99.0%] | Significant (p < 0.05) |
| 3. NWP Post-Processing | Raw NWP: 1.5217°C | Ridge: 0.918°C | Temperature MAE (°C) | -0.6037°C [0.5486, 0.6596] | Improvement excludes 0 |
| 4. Intent Classification | LLM: 97.0% (59.1487ms) | Encoder: 98.0% (0.0477ms) | Accuracy & Latency | 1240.0x speedup | Sub-millisecond latency |
| 5. Translation Strategy | Native: 84.0% | Cascaded: 100.0% | Number Preservation | +16.0% [10.0%, 24.0%] | Significant (p < 0.05) |

---

## 7. Data Provenance & Reproducibility

- **Golden Sets**: 11 recorded city fixtures from Open-Meteo (`eval/fixtures/open_meteo/`).
- **Advisories & Knowledge**: Public NDMA guidelines and ICAR crop alerts recorded in `seeds/knowledge/sources.csv`.
- **Alert Feeds**: Real NDMA SACHET CAP fixtures (`eval/fixtures/sachet/`).
- **Judged Samples**: Cohen's kappa agreement $\kappa = 0.76$ on 20 human-scored cases (`eval/golden/human_sample.json`).
- **Report Generated**: `2026-11-23T03:29:33.640743+00:00`
