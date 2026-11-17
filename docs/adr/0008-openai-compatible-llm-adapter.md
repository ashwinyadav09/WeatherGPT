# 0008: One OpenAI-compatible LLM adapter (Groq and OpenRouter)

**Status:** accepted (14 November 2026)

**Context:** The product owner already has Groq and OpenRouter keys. Both expose an OpenAI-compatible interface, with tool calling on supported models.

**Decision:** The LLM gateway ships one OpenAI-compatible adapter configured by base URL and key, plus a test stub. A main model (OpenRouter) and a fast model (Groq) are chosen by golden-set results, must support tool calling, and live in configuration. Sarvam and Gemini adapters can be added later without changes elsewhere.

**Consequences:** No new key is needed to start. Hindi quality and tool-calling reliability vary by model, so the golden set decides. Free tiers and logging policies differ, so real users' text goes only through a provider whose data policy has been checked.
