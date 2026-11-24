# LLM and Sarvam Call Cache (Ticket R20.4)

Directory storing recorded responses from real LLM and Sarvam API calls.
Keyed by sha256 of `(provider, model, messages, parameters)`.
Each file contains:
- `cache_key`
- `provider`
- `model`
- `messages`
- `parameters`
- `response`
- `latency_ms`
- `token_counts`
- `timestamp`
- `provenance: recorded_real_http`
- `replayed` (true on replay, false on initial recording)
