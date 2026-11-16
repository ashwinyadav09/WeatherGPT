# Seeds

Starting prompts, glossary, templates and UI strings. Tickets copy them into the runtime locations (`services/api/app/prompts/`, `services/api/app/i18n/`, `apps/web/src/i18n/`) and from then on the runtime copies are the source of truth; edit those, not these.

Hindi text here is a draft written for review. A native speaker must sign it off before release (a human-only step); never block work on it. Alert wording must stay close to official IMD and NDMA phrasing.

| File | Used by ticket |
|---|---|
| prompts/system.md, prompts/compose.md, tools.yaml | 02 |
| prompts/intent-baseline.md | 04, 15 |
| i18n/glossary.*.yaml, i18n/uncertainty.*.yaml | 02, 04 |
| i18n/alert-templates.yaml | 05 |
| i18n/ui.*.json | 01c, 20 |
| guidance/README.md | 10 |
| eval/golden.example.yaml | 02, 04 |
