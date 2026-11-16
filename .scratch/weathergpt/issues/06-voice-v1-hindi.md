# 06: Voice v1 (Hindi)

**What to build:** A user holds a button, speaks a weather question in Hindi and hears the answer, with a transcript on screen, replay and slow-down. When a place name is uncertain, the app reads it back for a yes or no.

**Blocked by:** 04

**Owner:** pradeep | **Reviewer:** ashwin

**Status:** ready-for-agent

- [ ] Push-to-talk with streaming recognition and a visible transcript
- [ ] Browser microphone capture works in Chrome and Firefox and on Android Chrome; recordings are converted to the format each provider needs
- [ ] The SpeechGateway has two provider adapters (Bhashini and one other) that both pass the conformance suite
- [ ] Uncertain place names are read back and confirmed
- [ ] Speech output reads units, degrees and times naturally
- [ ] Recognition errors are measured on at least 100 consented or field-like utterances, with place names and numbers scored separately
- [ ] First audio arrives within 3.5 seconds at p95 on 4G in instrumented runs
- [ ] No raw audio is kept by default; the consent notice covers voice
