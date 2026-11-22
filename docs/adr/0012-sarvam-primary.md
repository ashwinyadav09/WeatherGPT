# 0012: Sarvam is the primary speech and translation provider

**Status:** accepted (22 November 2026)

**Context:** The speech gateway used Bhashini as the primary provider and fell back to a canned transcript when no key was present, so Sarvam was never reached. Translation had no gateway; the agent relied on the LLM alone.

**Decision:** Sarvam (`api.sarvam.ai`) is the primary provider for both speech (STT/TTS) and translation. Bhashini remains in the repository but is dormant. When `SARVAM_API_KEY` is absent, voice endpoints return HTTP 503 and the web app hides the microphone. No canned transcripts are ever returned to users. A new translation gateway (`gateways/translation/`) uses Sarvam with an LLM fallback (Groq with the glossary in the system prompt) and a disk cache. Endpoints and language codes are recorded in `docs/integration-notes.md` from the current Sarvam documentation before any code is written.

**Consequences:** Voice and translation depend on `SARVAM_API_KEY`. The web UI conditionally renders the microphone based on `/v1/voice/health`. The free-credit balance must be monitored; the translation cache and pre-translated static strings reduce live calls.
