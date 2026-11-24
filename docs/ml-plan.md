# Models: What to Use, What We Trained, and Measured Results

## Architecture Overview
WeatherGPT uses a grounded hybrid AI architecture:
1. **Pretrained Foundation Models**: Handle conversational dialogue, explanation, and translation.
2. **Deterministic Tools**: Supply all factual numbers (forecasts, observations, alerts, and climate statistics) behind an *evidence packet*.
3. **Specialized In-House Models**: Five modular ML services providing fast local routing, statistical bias correction, climatological normals, multi-hazard risk assessment, and official advisory retrieval without cloud LLM dependencies.
4. **Vetted Knowledge Retrieval (RAG)**: Surfaces official NDMA disaster guidelines and ICAR agromet advisory chunks with hybrid dense and lexical search.
5. **Rigorous Grounding Verification**: Verifies every numerical value before presentation, falling back to deterministic templates if ungrounded.

---

## 1. Deployed Components & Providers

| Component | Model / Provider | Operational Role |
|---|---|---|
| Dialogue & Explanation | Groq / OpenRouter tool-calling models (e.g. Llama-3.3-70B, Qwen-2.5-72B) | Natural language explanation and summarisation; never invents numbers. |
| Intent Classification | TF-IDF / Multilingual MiniLM & Logistic Regression (`ml/intent/`) | Microsecond classification across 7 archetypes: `current`, `forecast`, `alert`, `advisory`, `climate`, `explain`, `unsafe`. |
| Point Forecast Bias Correction | Ridge Regression & LightGBM MOS models (`ml/bias_correction/`) | Corrects systematic 2m temperature bias from global NWP models over 15 Indian stations. |
| Climate Normals & Trends | ERA5 30-year climatological normal models (`ml/climate/`) | Computes historical 30-year normal, observed anomaly, percentile, and decadal trend note. |
| Extreme-Event Risk Outlook | Calibrated LightGBM models (`ml/extreme_event/`) | Estimates calibrated probabilities for heat waves, heavy rainfall, and cold waves with SHAP drivers. |
| Advisory Retrieval (RAG) | Hybrid BM25 + Dense `intfloat/multilingual-e5-small` (`ml/rag/`) | Indexes 20 clean chunks from 32 official NDMA and ICAR publications. |
| Speech-to-Text (ASR) | Sarvam AI `saaras:v3` | ASR across 7 Tier-1 Indic languages (voice-optional). |
| Text-to-Speech (TTS) | Sarvam AI `bulbul:v3` | High-fidelity Indic voice synthesis for weather advisories. |
| Translation Gateway | Sarvam Translate / IndicTrans2 with numeric placeholder protection | Preserves digits and units during cross-lingual synthesis. |

*(Note: IMD adapters remain dormant behind `IMD_ENABLED` flag per ADR 0011; NDMA SACHET is the active official warning source and Open-Meteo is the primary model guidance provider).*

---

## 2. In-House Trained Models & Evaluation Status

Status of model evaluations and ablations following Section 2 Truthfulness Rules:

### A. Intent Classification Model (`ml/intent/`)
- **Task**: Classify incoming queries into 7 discrete archetypes with place and temporal slot extraction.
- **Data & Training**: Trained on MASSIVE dataset (4,842 rows across 5 languages) using TF-IDF and Logistic Regression.
- **Validation Metrics**: Validation accuracy = **79.2%** (95% CI: `[76.2%, 82.2%]`), precision at tau = **0.9543**, macro-F1 = **0.63**.
- **Gold Set & Comparative Latency**: **`NOT MEASURED`** (Gold set evaluation pending human gold set task H1; live comparative latency evaluation against cloud LLM function calling scheduled in R20.7/R20.11).

### B. Point-Forecast Bias Correction (Model Output Statistics, `ml/bias_correction/`)
- **Task**: Reduce systematic temperature errors of raw NWP global models across Indian climate zones.
- **Data & Training**: 5,601 paired observations across 15 Indian stations.
- **Models Evaluated**: Raw NWP baseline vs Ridge MOS vs LightGBM MOS.
- **Measured Performance**:
  - Raw NWP Baseline: **1.1799°C** MAE (95% CI: `[1.1445°C, 1.2153°C]`)
  - Ridge MOS / LightGBM MOS: **1.0937°C** MAE (95% CI: `[1.0499°C, 1.1374°C]`)
  - **Improvement Delta**: **-0.0862°C** reduction in MAE (95% bootstrap confidence interval strictly excluding zero: `[0.0267°C, 0.1400°C]`, p < 0.05).
- **Extension & Baselines**: Data window extension to 2026, distinct baselines (persistence, climatology, trailing 30-day mean error), and per-lead evaluation scheduled in ticket R20.6.
- **Policy Enforcement**: Corrected outputs are strictly labeled as model guidance (Tier 4). Official alerts (Tier 1) are never modified.

### C. Climate Normals & Anomaly Models (`ml/climate/`)
- **Task**: Supply climatological context by comparing current conditions against 30-year reference baselines (1991–2020) derived from ERA5 hourly reanalysis archives.
- **Features**: Aggregated monthly mean, standard deviation, percentile ranks, and decadal anomaly trend.
- **Validation**: Full benchmark on 15 documented events and 15 deterministic controls across 20 grid cells scheduled in ticket R20.9.

### D. Extreme-Event Risk Outlook (`ml/extreme_event/`)
- **Task**: Provide multi-hazard risk probabilities (heat wave, heavy rainfall, cold wave) for Indian districts.
- **Architecture**: Stage 2 calibrated LightGBM binary classifiers with SHAP TreeExplainer feature importance attribution.
- **Metrics**: Accuracy = **93.9%**, Macro F1 = **0.800** on held-out evaluation block (5,601 samples).
- **Extension**: New 2025–2026 split, station normals, and leave-one-station-out evaluation scheduled in ticket R20.8.
- **Safety Policy**: Outputs display a prominent non-warning disclaimer: *"This is model-derived risk guidance, not an official government warning. Official alerts are issued by NDMA SACHET."*

### E. Advisory RAG Engine (`ml/rag/`)
- **Task**: Provide actionable crop and extreme weather advice without LLM hallucination.
- **Corpus & Extraction**: Rebuilding knowledge corpus by extracting text page-by-page from 33 real downloaded PDFs with extraction quality tracking scheduled in ticket R20.10.
- **Evaluation**: Retrieval metrics on human queries (H2) and citation precision scheduled in R20.10.
- **Ablation**: Grounding pass rate and citation support with and without retrieval scheduled in R20.11.

### F. Cascaded Translation with Placeholder Protection
- **Task**: Multilingual response generation without numerical corruption or hallucination.
- **Architecture**: Regex placeholder shielding (`__NUM_0__`, `__UNIT_0__`) applied before translation to protect forecast quantities across Indic scripts.
- **Ablation**: Comparative evaluation over 100 evidence-grounded answers measuring numeric preservation and sacrebleu chrF scheduled in ticket R20.11.

---

## 3. Strict Prohibitions
- **Never train a weather forecasting model from scratch**: Operational global NWP and official warnings have superior physics, satellite assimilations, and supercomputing capacity.
- **Never train an LLM to memorise weather facts**: Weather facts are dynamic and must come strictly from tool evidence packets.
- **Never use machine learning to generate or modify official emergency alerts**: Alerts from NDMA SACHET must be relayed verbatim as issued.
