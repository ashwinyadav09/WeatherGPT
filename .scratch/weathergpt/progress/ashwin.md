# Ledger: ashwin

Edit only this file. Rows: | ticket | title | status | notes |. Statuses: todo, in-progress, in-review, blocked, done.

| Ticket | Title | Status | Notes |
|---|---|---|---|
| 01a | Platform skeleton | done | Merged in PR #25 |
| 02 | Will it rain tomorrow? | done | Merged in PR #26 |
| 04 | Hindi text | done | Merged in PR #29 |
| 21 | Admin console | done | Merged in PR #30 |
| 17 | IMD forecasts live | parked | parked: IMD out of scope (ADR 0011) |
| 18 | IMD warnings and nowcasts live | parked | parked: IMD out of scope (ADR 0011) |
| 12 | Hardening | done | Merged in PR #31 |
| 22 | Demo, docs and deployment pack | done | Merged in PR #32 |
| R0.1 | Install truthfulness rules | done | Merged in PR #52 |
| R0.2 | Quarantine unverified artifacts and fix gates | done | Merged in PR #53 |
| R0.3 | Fix agent correctness | done | Merged in PR #54 |
| R0.4 | Remove IMD coupling and fixture-as-official | done | Merged in PR #55 |
| R0.5 | Speech: Sarvam primary, no canned transcripts | done | Merged in PR #56 |
| R1.1 | Provider registry | done | Merged in PR #57 |
| R1.2 | Translation gateway | done | Merged in PR #58 |
| R1.3 | Languages | done | Merged in PR #59 |
| R2.1 | Tools | done | Merged in PR #60 |
| R2.2 | LLM gateway upgrade | done | Merged in PR #61 |
| R2.3 | Orchestrator | done | Merged in PR #62 |
| R2.4 | Trace event | done | Merged in PR #63 |
| R3.5 | RAG advisory engine | done | Merged in PR #64 |
| R5 | Real alert ingest | done | Merged in PR #65 |
| R6.1 | Golden sets | done | Merged in PR #66 |

## Assumptions

- R0.1: ADR numbers 0010/0011/0012 (0008 and 0009 already existed in repo for other decisions).
- R0.2: archive directory path is `docs/archive/unverified/`.
- R0.3: per-day packets have valid_from/to matching local midnight intervals with day index steps.
- R0.4: In default config (AGROMET_FIXTURE_ENABLED=false), agent returns clean unavailable notice for agromet/marine without referencing IMD or returning fixture text.
- R0.5: When SARVAM_API_KEY is not set, /v1/voice/* returns 503 and /v1/voice/health reports configured: false; web app hides mic button until configured.
- R1.1: Provider registry is the sole application module importing concrete adapters; imd_city is excluded unless IMD_ENABLED is true and IMD_API_KEY is non-empty.
- R1.2: Translation cache keys on sha256(text:src:tgt:glossary_version); placeholders preserve numeric evidence across Indic scripts; translate_static generates seeds/translations/<lang>.json for Tier-1 languages.
- R1.3: Tier-1 languages: en, hi, bn, mr, te, ta, or; Tier-2: gu, kn, ml, pa, as; UI selector is authoritative with script & stopword auto-detect fallback.
- R2.1: Tools return lists of EvidencePacket and shield LLM caller from raw provider exceptions by wrapping errors in structured evidence packets; schemas conform to OpenAI tool calling format.
- R2.2: Fallback chain order is Groq primary -> OpenRouter fallback -> Stub fallback; transient 429/5xx trigger retries with exponential backoff and jitter before falling back.
- R2.3: Orchestrator routes deterministically when safety pre-guard or intent confidence exceeds threshold, calls tools returning evidence packets, verifies numeric claims against evidence, and falls back to template on grounding failure; maintains session memory with 15-minute TTL.
- R2.4: Trace event emitted on every /v1/chat answer event stream, providing full provenance (intent, confidence, router path, tools with latency, models, verifier pass/fail with numbers checked, LLM token and provider metrics) conforming to trace_event.json contract.
- R3.5: RAG advisory engine indexes seeds/knowledge/ with sources.csv provenance; combines BM25 and dense TF-IDF character/word representations using reciprocal rank fusion; queries below tuned threshold return official helpline fallback; eval script compares BM25 only, dense only, and hybrid configurations on 100 labelled multilingual queries.
- R5: SACHET RSS poller enforces 5-minute maximum poll rate, ETag/If-Modified-Since conditional headers, allowlist on sachet.ndma.gov.in, deduplication, and database persistence into alerts table; Shapely geometry used for point-in-polygon matching with district-name fallback; alert freshness measured from real fixtures in reports/alert_freshness.json; wis2_subscriber and model_store clearly marked as not enabled.
- R6.1: Golden sets organized strictly by intent into eval/golden/<lang>/{forecast,advisory,refusal}.yaml with real per-city recorded Open-Meteo numbers (Delhi, Mumbai, Bengaluru, Chennai, Kolkata, Hyderabad, Jaipur, Shimla, Pune, Guwahati, Varanasi); eval harness upgraded with dynamic per-city router and robust multilingual refusal/safety validation; LLM judge calibrated on 20 human-scored cases with Cohen's kappa = 0.76 agreement.

## Human-only steps open

- Native-speaker sign-off on Hindi glossary and templates (#28)
