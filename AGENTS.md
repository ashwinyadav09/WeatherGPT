# WeatherGPT

A grounded, multilingual, voice-first weather assistant for India. A non-commercial, public-interest pilot, delivered as a website (progressive web app) with no native app.
The LLM explains. Tools supply facts. Official warnings are relayed as issued.
Three people work on it through GitHub: Ashwin (lead), Aman and Pradeep, each with their own AI agent.

## Always
- Give every number an *evidence packet*: source, authority tier, issue time, validity, attribution.
- Climb the *authority ladder*: official warning > official forecast > national model > global model > aggregator. The LLM narrates; it adds no facts.
- Relay alerts through vetted templates. Read `.agents/rules/alerts-relay-only.md` before touching alert code.
- Put each external system (data, speech, LLM) behind an *adapter*. A *seam* has two adapters or one recorded fixture.
- Go *red* first: write the failing test, then the code. Take expected values from recorded fixtures or hand-checked examples.
- Keep keys in environment variables, never in the repository or in chat.
- Keep the product free of ads, payments and resale of source data.
- IMD is out of scope; adapters dormant behind `IMD_ENABLED` flag (ADR 0011). Name the source that really answered (e.g., "Open-Meteo (global model)"). See `.scratch/weathergpt/REMEDIATION_PLAN.md` for all remaining work.
- Work for one named person: `docs/AUTOPILOT.md` is your operating manual. Decide, don't ask; repair your own errors.

## Read before you act
- Creating files or services: `docs/architecture.md`. Calling an outside system: `docs/integration-notes.md`.
- Building pages: `docs/ui-spec.md`. Prompts, glossary, templates, UI strings: `seeds/`.
- Evals and acceptance: `docs/eval-and-acceptance.md`. A command or test fails: `docs/troubleshooting.md`.
- Team rules, ownership, branches, reviews: `docs/team.md`. Keys and models: `docs/api-keys.md`, `docs/ml-plan.md`.
- Vocabulary: `GLOSSARY.md`. Decisions: `docs/adr/`. Spec: `.scratch/weathergpt/SPEC.md`.
- Tickets and order: `.scratch/weathergpt/issues/`. Assignments: `team/assignments.csv`. Ledgers: `.scratch/weathergpt/progress/`.
- Procedures: `.agents/skills/` (add-data-source, add-language, add-alert-template, run-eval, open-pr, fix-ci, resolve-merge-conflicts, review-pr).

## Commands
`python scripts/dev.py doctor | up | down | test | lint | eval --lang hi | replay-alerts | contracts | acceptance | ci | secret-scan | progress` (a Makefile wraps these, for example `make ci`).

## Done means
Merged to main through a reviewed pull request, CI green, acceptance boxes ticked with proof, ledger updated.
