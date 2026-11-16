---
trigger: glob
globs: "**/i18n/**, **/templates/**, **/glossary/**"
description: Language, glossary and alert-template rules; native-speaker review gate for every new language.
---

# Languages, glossary and templates

- Language tiers: A voice in and out, B voice in and text out, C text and vetted alert templates.
- Keep one glossary per language: weather terms, units, hazard names, alert levels. Inject it into prompts and check it after generation.
- Build alert templates by hazard x severity x action from official IMD or NDMA wording; slots only for place and time.
- Check each template by back-translation, then record a native-speaker sign-off before it ships.
- Handle code-mixed input (for example Hindi with English words) and local numerals.
- Normalise text for speech: units, degrees and times become natural spoken forms per language.
- Add a language only through the `add-language` skill.
