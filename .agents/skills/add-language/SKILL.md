---
name: add-language
description: Add a new language. Use when a ticket adds Bengali, Marathi, Tamil, Telugu or any other scheduled language.
---

# Add a language

1. Confirm the tier (A, B or C) and check that ASR and TTS providers support it. Done when the provider matrix row is filled.
2. Create the glossary: weather terms, units, hazards, alert levels. Done when every glossary key exists.
3. Create alert templates for each hazard x severity x action from official wording, and back-translate each. Done when every template has a back-translation.
4. Build the golden set (at least 300 cases across archetypes, fixture-based) and run `python scripts/dev.py eval --lang <code>`. Done when the thresholds pass.
5. Ask a native speaker to review the glossary, the templates and a sample of answers; record the sign-off in the ticket. This step needs a human.
6. Enable the language behind a flag, add it to the per-language dashboard, then release.

Done means: golden thresholds pass and a native-speaker sign-off is recorded.
