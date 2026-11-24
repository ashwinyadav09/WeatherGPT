# WeatherGPT Acceptance Gates Report (2026-11-24)

| Parameter | Gate | Target | Measured | Status |
|---|---|---|---|---|
| Accuracy & Relevance | Unit & seam tests | 100% pass | PASS | ✅ PASS |
| Accuracy & Relevance | EN Golden Set | >= 95% | 48/48 (100.0%) | ✅ PASS |
| Accuracy & Relevance | HI Golden Set | >= 95% | 318/318 (100.0%) | ✅ PASS |
| Accuracy & Relevance | BN Golden Set | >= 95% | 317/318 (99.7%) | ✅ PASS |
| Accuracy & Relevance | MR Golden Set | >= 95% | 316/318 (99.4%) | ✅ PASS |
| Accuracy & Relevance | TE Golden Set | >= 95% | 310/318 (97.5%) | ✅ PASS |
| Accuracy & Relevance | TA Golden Set | >= 95% | 318/318 (100.0%) | ✅ PASS |
| Accuracy & Relevance | OR Golden Set | >= 95% | 18/18 (100.0%) | ✅ PASS |
| Response Latency | TTFT p95 | <= 1500 ms | 41.26 ms | ✅ PASS |
| Response Latency | Total duration p95 | <= 3000 ms | 41.45 ms | ✅ PASS |
| Scalability | Load 20 concurrent users p95 | <= 1500 ms | 107.1 ms | ✅ PASS |
| Scalability | Load 50 concurrent users p95 | <= 1500 ms | 309.4 ms | ✅ PASS |
| Scalability | Load 100 concurrent users p95 | <= 1500 ms | 786.0 ms | ✅ PASS |
| Accessibility | WCAG 2.2 AA automated axe-core | 0 violations | 0 violations | ✅ PASS |
| Voice & Speech | Speech ASR across 7 languages | WER <= 15%, entity <= 5% | NOT MEASURED | ⚠️ N/A |
| Model & Agent Ablations | 5 core ablation studies | All 5 completed & significant | 5/5 ablations evaluated | ✅ PASS |
| Infrastructure | Secret scan | 0 secrets | PASS | ✅ PASS |
| Infrastructure | Single Alembic head | Exactly 1 head | PASS | ✅ PASS |
| Infrastructure | Contract tests | All pass | PASS | ✅ PASS |

**Overall**: UNKNOWN (gates missing)
**Generated**: 2026-11-24T18:51:56.611445+00:00
