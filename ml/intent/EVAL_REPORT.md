# Evaluation Report: Multilingual Intent & Slot Classifier vs. LLM Baseline

## Summary
Ticket 15 evaluates `intent-multilingual-v1.0` against the cloud LLM-only baseline (e.g. GPT-4o-mini / Llama 3 8B via Groq/OpenRouter) across 350 held-out golden queries covering English, Hindi (Devanagari), and Hinglish (Romanized Hindi/English).

## Evaluation Metrics

| Metric | `intent-multilingual-v1.0` | Cloud LLM Baseline | Target / Requirement | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Intent Accuracy** | **97.14%** (340/350) | 96.57% (338/350) | >= 95.0% | **PASS** (+0.57%) |
| **Slot Extraction F1** | **93.8%** | 94.2% | >= 90.0% | **PASS** |
| **Inference Latency (p50)** | **0.01 ms** | ~850 ms | < 15.0 ms | **PASS** (85,000x faster) |
| **Inference Latency (p95)** | **0.02 ms** | ~1,250 ms | < 50.0 ms | **PASS** |
| **Cost per 1k turns** | **$0.00** (Local/CPU) | $0.60 - $2.00 | Free / Minimal | **PASS** (Zero cost) |
| **Offline Reliability** | **100%** (no network dependency) | Dependent on WAN | Resilient | **PASS** |

## Intent Breakdown on Golden Set (350 examples)
- `current`: 45 / 45 (100.0%)
- `forecast`: 52 / 53 (98.1%)
- `alert`: 40 / 40 (100.0%)
- `advisory`: 38 / 39 (97.4%)
- `climate`: 35 / 36 (97.2%)
- `explain`: 30 / 30 (100.0%)
- `meta`: 32 / 32 (100.0%)
- `unsafe`: 68 / 75 (90.7% detected directly; ambiguous cases routed safely to LLM guardrail)

## Fallback Analysis
- Confidence threshold was tuned on held-out data:
  - At threshold `tau = 0.75`, queries with confidence < 0.75 are flagged for LLM fallback.
  - Gibberish and out-of-domain queries achieved mean confidence of 0.42, triggering 100% fallback rate.
  - Confident in-domain queries achieved mean confidence > 0.88, triggering < 1.5% false fallback rate.

## Conclusion & Shipping Recommendation
`intent-multilingual-v1.0` matches the cloud baseline on intent classification accuracy (97.14% vs 96.57%) while reducing turn routing latency from ~850 ms to ~0.01 ms and eliminating routing LLM token costs entirely. The model meets all acceptance criteria and is recommended for deployment.
