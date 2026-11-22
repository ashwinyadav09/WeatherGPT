> [!CAUTION]
> **UNVERIFIED: generated from simulated data. Do not cite.**
> Archived 2026-11-22 (R0.2). See docs/archive/unverified/README.md.

---
# LLM Model Selection Report (Prompt X)

## Summary of Selections
- **Main Role**: `llama-3.3-70b-versatile` (groq)
  - TTFT: 210.0 ms | p95 latency: 679.2 ms | Cost: $0.3406 / 1k queries
  - Groundedness: 99.8% | Intent Accuracy: 99.0%
- **Fast Role**: `llama-3.1-8b-instant` (groq)
  - TTFT: 95.0 ms | p95 latency: 263.6 ms | Cost: $0.0301 / 1k queries
  - Groundedness: 98.2% | Intent Accuracy: 96.5%

## All Evaluated Candidates
| Role | Provider | Model | TTFT (ms) | p95 (ms) | Cost/1k queries | Groundedness | Gates Met |
|---|---|---|---|---|---|---|---|
| main | groq | `llama-3.3-70b-versatile` | 210.0 | 679.2 | $0.3406 | 99.8% | ✅ Yes |
| main | openrouter | `meta-llama/llama-3.3-70b-instruct` | 520.0 | 2476.9 | $0.2180 | 99.8% | ✅ Yes |
| main | openrouter | `qwen/qwen-2.5-72b-instruct` | 610.0 | 2921.6 | $0.1955 | 99.8% | ✅ Yes |
| fast | groq | `llama-3.1-8b-instant` | 95.0 | 263.6 | $0.0301 | 98.2% | ✅ Yes |
| fast | openrouter | `meta-llama/llama-3.1-8b-instruct` | 340.0 | 1675.0 | $0.0300 | 98.2% | ✅ Yes |
| fast | openrouter | `google/gemini-2.0-flash-lite-preview-02-05:free` | 260.0 | 1173.2 | $0.0622 | 98.2% | ✅ Yes |

## Selection Rationale
1. **Groq LPU Acceleration**: Groq delivers sub-250ms TTFT on 70B models and sub-100ms on 8B models, satisfying the strict 1.5s TTFT p95 gate easily.
2. **Cost Efficiency**: `llama-3.1-8b-instant` on Groq costs only $0.05/$0.08 per 1M tokens ($0.0301 per 1,000 queries), making it ideal for the high-volume fast role.
3. **Fallback Architecture**: OpenRouter (`meta-llama/llama-3.3-70b-instruct` and `meta-llama/llama-3.1-8b-instruct`) provides OpenAI-compatible fallback with zero code changes when 429 or rate limits are reached.

