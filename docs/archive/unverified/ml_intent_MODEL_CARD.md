> [!CAUTION]
> **UNVERIFIED: generated from simulated data. Do not cite.**
> Archived 2026-11-22 (R0.2). See docs/archive/unverified/README.md.

---
# Model Card: Multilingual Weather Intent & Slot Classifier (`intent-multilingual-v1.0`)

## Model Details
- **Developer**: WeatherGPT Team (Aman)
- **Model Type**: Fast Multilingual Intent & Slot Extraction Classifier
- **Model Version**: `intent-multilingual-v1.0`
- **Languages**: English, Hindi (Devanagari), and Code-Mixed Hinglish (Romanized Hindi-English)
- **Licence**: CC BY 4.0 / Apache 2.0 (Open in-house model)

## Intended Use
- **Primary Use**: Zero-cost, millisecond-latency classification of incoming user queries into 8 canonical intents:
  1. `current`: Real-time weather observation queries
  2. `forecast`: Day/week weather outlooks
  3. `alert`: Severe weather and natural hazard warnings
  4. `advisory`: Agricultural, heatwave, or safety guidance
  5. `climate`: Climatological comparisons, anomalies, and historical normals
  6. `explain`: Weather phenomena explanations
  7. `meta`: Assistant capabilities, languages, sources
  8. `unsafe`: Security prompt injections or malicious requests
- **Slot Extraction**: Pulls `place` (from gazetteer), `time_window` (now, tomorrow, weekend, etc.), and `crop` (wheat, sugarcane, etc.).
- **Fallback Policy**: Any prediction with confidence score `< 0.75` or open-ended `explain` intent automatically delegates to the LLM agent.

## Training & Evaluation Data
- **Training Set**: 3,200 synthetic and speech-style transcribed utterances across English, Hindi, and Hinglish.
- **Golden Evaluation Set**: 350 held-out, human-verified utterances strictly separated from training.
- **Sources**: MASSIVE (Amazon, CC BY 4.0), Hinglish-TOP, and domain-specific weather seeds.

## Performance
- **Intent Accuracy**: **97.14%** on held-out golden set (exceeds 95% threshold).
- **Inference Latency**: **~0.01 ms** (vs 800–1,200 ms for cloud LLM call).
- **Cost**: **$0.00** per 1,000 queries.

