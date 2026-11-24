# WeatherGPT Acceptance Gates Report (2026-11-24)

| Parameter | Gate | Target | Measured | Status |
|---|---|---|---|---|
| Accuracy & Relevance | Unit & seam tests | 100% pass | PASS | ✅ PASS |
| Accuracy & Relevance | EN Golden Set | >= 95% | 48/48 (100.0%) [template-built cases over fixture data, not a product measurement] | ✅ PASS |
| Accuracy & Relevance | HI Golden Set | >= 95% | 318/318 (100.0%) [template-built cases over fixture data, not a product measurement] | ✅ PASS |
| Accuracy & Relevance | BN Golden Set | >= 95% | 317/318 (99.7%) [template-built cases over fixture data, not a product measurement] | ✅ PASS |
| Accuracy & Relevance | MR Golden Set | >= 95% | 316/318 (99.4%) [template-built cases over fixture data, not a product measurement] | ✅ PASS |
| Accuracy & Relevance | TE Golden Set | >= 95% | 310/318 (97.5%) [template-built cases over fixture data, not a product measurement] | ✅ PASS |
| Accuracy & Relevance | TA Golden Set | >= 95% | 318/318 (100.0%) [template-built cases over fixture data, not a product measurement] | ✅ PASS |
| Accuracy & Relevance | OR Golden Set | >= 95% | 18/18 (100.0%) [template-built cases over fixture data, not a product measurement] | ✅ PASS |
| Response Latency | TTFT p95 | <= 1500 ms | NOT MEASURED | ⚠️ N/A |
| Response Latency | Total duration p95 | <= 3000 ms | NOT MEASURED | ⚠️ N/A |
| Scalability | Load 20 concurrent users p95 | <= 1500 ms | NOT MEASURED | ⚠️ N/A |
| Scalability | Load 50 concurrent users p95 | <= 1500 ms | NOT MEASURED | ⚠️ N/A |
| Scalability | Load 100 concurrent users p95 | <= 1500 ms | NOT MEASURED | ⚠️ N/A |
| Accessibility | WCAG 2.2 AA automated axe-core | 0 violations | 0 violations | ✅ PASS |
| Voice & Speech | Speech ASR across 7 languages | WER <= 15%, entity <= 5% | NOT MEASURED | ⚠️ N/A |
| Model & Agent Ablations | 5 core ablation studies | All 5 completed & significant | NOT MEASURED | ⚠️ N/A |
| Infrastructure | Secret scan | 0 secrets | PASS | ✅ PASS |
| Infrastructure | Single Alembic head | Exactly 1 head | PASS | ✅ PASS |
| Infrastructure | Contract tests | All pass | PASS | ✅ PASS |

**Overall**: UNKNOWN (gates missing)
**Generated**: 2026-11-24T20:11:42.035778+00:00
