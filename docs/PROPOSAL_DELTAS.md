# WeatherGPT Proposal Deltas & Architectural Divergences

This document records every claim in the original WeatherGPT project proposal that has been revised, replaced, or clarified during implementation. These changes reflect adherence to Section 2 Truthfulness Rules, real-world API constraints, public-interest non-commercial licensing, and software engineering best practices.

The team will use this document to synchronize the formal project proposal PDF.

---

## Summary of Major Deltas

| # | Proposal Claim | Operational Implementation | Architectural Justification |
|---|---|---|---|
| **1** | Direct IMD API integration for forecasts, nowcasts, and alerts | NDMA SACHET (Official Warnings) + Open-Meteo (NWP Forecasts) | IMD adapters built but kept dormant behind `IMD_ENABLED=false` (ADR 0011). Ingests open CAP 1.2 alerts from NDMA SACHET. |
| **2** | Bhashini for all Indic ASR, TTS, and translation | Sarvam AI (`saaras:v3`, `bulbul:v3`) + local fallback | Bhashini keys are pending approval and were never used; Sarvam AI provides reliable speech and translation gateways. |
| **3** | Speculative performance targets in original proposal | Truthfulness rules: replace speculative targets with real measured baselines | Speculative targets are replaced by empirical baselines once models run on real data; unmeasured items are marked `NOT MEASURED`. |
| **4** | Mandatory voice-first interface requiring microphone | Voice-optional Progressive Web App (PWA) | Mandatory voice creates severe friction and privacy concerns; text and visual cards operate standalone. |
| **5** | Pilot aviation weather briefings (METAR/TAF) | Aviation queries recognized and answered with polite refusal (Decision D3) | Aviation safety is out of scope for a civilian weather pilot; aviation is not supported and directs users to certified DGCA/AAI portals. |

---

## Detailed Delta Analysis

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
  - Bhashini API keys are pending approval and were never used.
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

All documentation across the repository reflects these 5 deltas:
- `README.md`: Authority ladder, NDMA SACHET alerts, Open-Meteo guidance, Sarvam AI, 7 Tier-1 languages.
- `docs/architecture.md`: Ingest pipelines, trace panel SSE contract, MOS bias correction, RAG advisory engine.
- `docs/ml-plan.md`: FastText/MiniLM encoder, LightGBM/Ridge MOS models, ablation studies.
- `docs/eval-and-acceptance.md`: Automated acceptance gates, Section 2 truthfulness rules, dated result archives.
- `scripts/tasks/demo.py`: Walkthrough illustrating operational systems.
