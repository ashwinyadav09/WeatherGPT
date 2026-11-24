# WeatherGPT Proposal Deltas & Architectural Divergences

This document records every objective and claim in the original WeatherGPT project proposal that has been revised, replaced, or clarified during implementation. These changes reflect adherence to Section 2 Truthfulness Rules, real-world API constraints, public-interest non-commercial licensing, and software engineering best practices.

Every number below comes strictly from reproducible scripts reading real inputs and writing audited machine-readable result files (Rule T1 / T4). Unmeasured items are explicitly reported as `NOT MEASURED` (Rule T2).

The team will use this document to synchronize the formal project proposal PDF.

---

## Summary of Major Architectural Deltas

| # | Proposal Claim | Operational Implementation | Architectural Justification |
|---|---|---|---|
| **1** | Direct IMD API integration for forecasts, nowcasts, and alerts | NDMA SACHET (Official Warnings) + Open-Meteo (NWP Forecasts) | IMD adapters built but kept dormant behind `IMD_ENABLED=false` (ADR 0011). Ingests open CAP 1.2 alerts from NDMA SACHET. |
| **2** | Bhashini for all Indic ASR, TTS, and translation | Sarvam AI (`saaras:v3`, `bulbul:v3`) + local fallback | Bhashini keys are pending approval and were never used; Bhashini API keys are pending approval and were never used. Sarvam AI provides reliable speech and translation gateways. |
| **3** | Speculative performance targets in original proposal | Truthfulness rules: replace speculative targets with real measured baselines | Speculative targets are replaced by empirical baselines derived from real data; unmeasured items are marked `NOT MEASURED`. |
| **4** | Mandatory voice-first interface requiring microphone | Voice-optional Progressive Web App (PWA) | Mandatory voice creates severe friction and privacy concerns; voice is optional while text and visual cards operate standalone. |
| **5** | Pilot aviation weather briefings (METAR/TAF) | Aviation queries recognized and answered with polite refusal (Decision D3) | Aviation safety is out of scope for a civilian weather pilot; aviation is not supported and directs users to certified DGCA/AAI portals. |

---

## Proposal Objectives: Target vs. Measured Reality

In accordance with remediation requirements, each objective from the original project proposal is tracked below with its intended target, empirical measured value with confidence interval (or `NOT MEASURED`), and the architectural change:

### 1. Multilingual Golden Set Accuracy (Tier-1 Indic Languages)
- **Proposal Target**: >= 95.0% accuracy across conversational weather query archetypes in Indian languages.
- **Measured Value**: Template-built test cases evaluated over recorded weather fixtures:
  - English (`en`): **100.0%** (48/48 passed)
  - Hindi (`hi`): **100.0%** (318/318 passed)
  - Bengali (`bn`): **99.7%** (317/318 passed)
  - Marathi (`mr`): **99.4%** (316/318 passed)
  - Telugu (`te`): **97.5%** (310/318 passed)
  - Tamil (`ta`): **100.0%** (318/318 passed)
  - Odia (`or`): **100.0%** (18/18 passed)
- **Status / Note**: Template-built cases over fixture data, not a product measurement. Live end-to-end evaluation against recorded real city forecasts is scheduled in tickets R20.3 and R20.12.

### 2. Response Latency & Time to First Token (TTFT)
- **Proposal Target**: TTFT p95 <= 1500 ms; Total Turn Duration p95 <= 3000 ms.
- **Measured Value**: **`NOT MEASURED`**
- **Status / Note**: Undergoing live HTTP stack benchmarking in ticket R20.12 across Docker HTTP services with real LLM and Sarvam integration.

### 3. Concurrency Load Testing & Scalability
- **Proposal Target**: Concurrent streaming support at 20, 50, and 100 simultaneous users with p95 latency <= 1500 ms.
- **Measured Value**: **`NOT MEASURED`**
- **Status / Note**: Undergoing live multi-user ramp load testing on the Docker stack in ticket R20.12.

### 4. Speech Recognition (ASR) & Speech Synthesis (TTS)
- **Proposal Target**: Word Error Rate (WER) <= 15.0% across 7 Indic languages via Bhashini.
- **Measured Value**: **`NOT MEASURED`**
  - Reference transcripts prepared for 260 utterances across 7 languages (`eval/fixtures/speech/`).
  - Real voice audio recordings pending human field collection task H3 per Rules T1, T2 & S1.
- **What Changed**: Bhashini API keys are pending approval and were never used. Migrated speech gateway to Sarvam AI (`saaras:v3` for ASR, `bulbul:v3` for TTS). Speech recognition is voice-optional and evaluated only against real audio once task H3 is collected.

### 5. Point-Forecast Bias Correction (Model Output Statistics)
- **Proposal Target**: Statistically significant reduction in 2m temperature forecast error over raw global NWP models across Indian stations.
- **Measured Value**:
  - Raw NWP Baseline: **1.1799°C** MAE (95% CI: `[1.1445°C, 1.2153°C]`)
  - Ridge MOS / LightGBM MOS: **1.0937°C** MAE (95% CI: `[1.0499°C, 1.1374°C]`)
  - Improvement Delta: **-0.0862°C** MAE reduction (95% bootstrap CI: `[0.0267°C, 0.1400°C]`, p < 0.05).
- **Status / Note**: Prior split (2024 test block). Extended data window through 2026, additional baselines (persistence, climatology), and per-lead evaluation scheduled in ticket R20.6.

### 6. Intent Classification & Edge Routing
- **Proposal Target**: Fast, robust intent classification across weather queries without cloud round-trip delay.
- **Measured Value**:
  - Local Intent Model: Validation accuracy = **79.2%** (95% CI: `[76.2%, 82.2%]`), Macro-F1 = **0.63**, precision at tau = **0.9543**.
  - Gold Set Evaluation: **`NOT MEASURED`** (Pending H1 human gold set).
  - Comparative Latency & Speedup: **`NOT MEASURED`** (Scheduled for live comparison on validation split in R20.7/R20.11).
- **What Changed**: High precision threshold (tau) routes queries locally; low-confidence queries safely fall back to LLM or deterministic routing.

### 7. Advisory RAG Retrieval & Knowledge Grounding
- **Proposal Target**: Agricultural and disaster safety advice grounded in vetted official documents without hallucination.
- **Measured Value**: **`NOT MEASURED`**
- **Status / Note**: Corpus rebuild from 33 real downloaded PDFs and evaluation with human-verified queries (H2) scheduled in ticket R20.10.

### 8. Cross-Lingual Number & Unit Preservation
- **Proposal Target**: Multilingual Indic generation without numerical drift or hallucination of temperatures and rainfall amounts.
- **Measured Value**: **`NOT MEASURED`**
- **Status / Note**: Systematic evaluation of cascaded translation versus native generation over 100 evidence-grounded answers scheduled in ticket R20.11.

### 9. Accessibility (WCAG 2.2 AA)
- **Proposal Target**: Full compliance with WCAG 2.2 Level AA accessibility standards.
- **Measured Value**:
  - Automated `@axe-core/playwright` audit: **0 violations** across 5 core views (`/`, `/#alerts`, `/#places`, `/#more`, `/offline.html`).
  - Physical screen reader testing (NVDA, TalkBack): **`NOT MEASURED`** (requires human tester on physical hardware).
- **What Changed**: Automated accessibility audit integrated into acceptance test suite. Screen reader validation honestly marked `NOT MEASURED` until human testing.

### 10. Emergency Alert Dissemination & Freshness
- **Proposal Target**: Real-time ingest and display of official government weather warnings.
- **Measured Value**:
  - Authentic NDMA SACHET CAP 1.2 alerts replayed: **26 alerts** verified with polygon matching and verbatim preservation.
  - Live 48h alert poller freshness: **`NOT MEASURED`** (< 5 live alerts observed during test window per Rule S1 / R18.6).
- **What Changed**: Direct IMD warning scraper replaced by NDMA SACHET CAP 1.2 RSS/XML feed. Alerts are relayed verbatim without LLM paraphrasing.

### 11. LLM Judge Calibration
- **Proposal Target**: Automated LLM evaluation of answer quality.
- **Measured Value**: **`NOT MEASURED`** (Pending independent human rater scoring task H4 per Rule T1/T2).
- **What Changed**: Evaluator calibration requires human rater ground truth (H4). Until H4 is completed, automated judge scores are excluded from acceptance claims.

### 12. Aviation Weather Briefings (METAR/TAF)
- **Proposal Target**: Pilot aviation briefings decoding METAR and TAF reports from Indian airports.
- **Measured Value**: **`DEPRECATED / NOT SUPPORTED`**
- **What Changed**: Aviation safety is out of scope for a civilian weather pilot (Decision D3). Aviation queries are recognized by intent classification and politely refused, directing pilots to official DGCA/AAI flight dispatch portals. Aviation is not supported.

---

## Detailed Architectural Divergence Analysis

### 1. IMD Feeds Replaced by NDMA SACHET & Open-Meteo

- **Original Claim**: Direct API consumption from the India Meteorological Department (IMD) for district-level forecasts, city nowcasts, and official severe weather warnings.
- **Why It Changed**:
  - IMD API access is governed by formal governmental data-sharing protocols with vetting periods. IMD keys are pending approval and were never used.
  - Relying on unverified scrapers would violate terms of service and truthfulness rules.
- **Operational Reality**:
  - **Official Emergency Warnings (Tier 1)**: Ingested directly from the National Disaster Management Authority (NDMA) SACHET Common Alerting Protocol (CAP 1.2) XML/RSS feed. These alerts are official government warnings and are relayed verbatim without LLM alterations.
  - **Operational Forecasts (Tier 5)**: Sourced from Open-Meteo (under CC BY 4.0), providing global NWP model outputs (ECMWF IFS, GFS).
  - **IMD Adapter Status**: IMD client adapters are fully coded and tested against recorded fixtures but remain dormant behind the `IMD_ENABLED=false` configuration flag (ADR 0011).

### 2. Speech & Translation Infrastructure: Bhashini to Sarvam AI

- **Original Claim**: Exclusive reliance on the Government of India's Digital India Bhashini ecosystem for all Automated Speech Recognition (ASR), Text-to-Speech (TTS), and Indic translation.
- **Why It Changed**:
  - Bhashini API keys are pending approval and were never used; Bhashini keys are pending approval and were never used.
- **Operational Reality**:
  - **Primary Speech Gateway**: Integrated Sarvam AI (`saaras:v3` for ASR and `bulbul:v3` for Indic speech synthesis).
  - **Translation Safety**: Multilingual query and response handling utilizes cascaded translation with numerical regex placeholder protection (`__NUM_0__`, `__UNIT_0__`), ensuring preservation of forecast quantities across Indic languages.

### 3. Re-Confirmation of Performance Targets Against Real Baselines

- **Original Claim**: The project proposal stated speculative performance targets without empirical measurement.
- **Why It Changed**:
  - Under Section 2 Truthfulness Rules, every number reported in code, documentation, or presentations must come from a reproducible script that reads real inputs and writes a machine-readable result file. Hand-typed or speculative targets are strictly prohibited.
- **Operational Reality**:
  - Performance targets must be re-confirmed against measured baselines derived from real data.
  - Where real data or live experiments have not yet been completed, parameters are documented honestly as `NOT MEASURED`.

### 4. Voice Interaction: Optional PWA Capability Rather Than Mandatory Gate

- **Original Claim**: "Voice-first only" interface with mandatory audio prompt on page load.
- **Why It Changed**:
  - Browser auto-play and microphone permission policies block unsolicited audio capture.
  - Users in noisy agricultural fields or low-connectivity zones experience high speech recognition drop-off.
- **Operational Reality**:
  - WeatherGPT is built as a responsive Progressive Web App (PWA) where voice is optional.
  - Voice input (STT) and voice playback (TTS) are accessible via a microphone toggle, but all forecasts, risk cards, and emergency warnings render immediately in structured text and visual cards without requiring microphone authorization.

### 5. Aviation Briefings (METAR/TAF) Deprecated

- **Original Claim**: Support for pilot aviation weather briefings (decoding METAR and TAF reports from Indian airports).
- **Why It Changed**:
  - Aviation weather is a specialized mission-critical domain regulated by the Directorate General of Civil Aviation (DGCA) and the Airports Authority of India (AAI). Providing unofficial conversational summaries of METAR reports introduces safety hazards and regulatory liability inappropriate for a general public-interest weather pilot (Decision D3). Aviation is not supported.
- **Operational Reality**:
  - Airport METAR decoders and mathematics have been isolated in unit tests.
  - The conversational intent classifier explicitly identifies aviation queries and returns a polite refusal message explaining that aviation is not supported in this civilian pilot and directing pilots to official DGCA/AAI flight dispatch portals.

---

## Document Alignment Verification

All documentation across the repository reflects these deltas:
- `README.md`: Authority ladder, NDMA SACHET alerts, Open-Meteo guidance, Sarvam AI, 7 Tier-1 languages.
- `docs/architecture.md`: Ingest pipelines, trace panel SSE contract, MOS bias correction, RAG advisory engine.
- `docs/ml-plan.md`: FastText/MiniLM encoder, LightGBM/Ridge MOS models, planned ablation studies.
- `docs/eval-and-acceptance.md`: Automated acceptance gates, Section 2 truthfulness rules, dated result archives.
- `scripts/tasks/demo.py`: Walkthrough illustrating operational systems with live audited metrics.
