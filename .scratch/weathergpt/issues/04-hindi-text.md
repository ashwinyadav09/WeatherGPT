# 04: Hindi text

**What to build:** A user can ask the same questions in Hindi, including Hindi mixed with English words, and get correct Hindi answers with weather terms and units in natural language and uncertainty explained in plain words.

**Blocked by:** 02

**Owner:** ashwin | **Reviewer:** pradeep

**Status:** ready-for-agent

- [ ] Language detection and Hindi answers work for every question type from ticket 02
- [ ] A Hindi glossary covers weather terms, units, hazards and alert levels, and is checked after generation
- [ ] A phrase map turns probabilities and IMD categories into plain Hindi
- [ ] The verifier handles Hindi numerals and unit spellings
- [ ] A Hindi golden set of at least 300 cases passes: groundedness 99 percent, intent and slots 95 percent
- [ ] Code-mixed cases are part of the set
- [ ] A native-speaker review is recorded (human step)
