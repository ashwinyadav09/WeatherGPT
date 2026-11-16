# WeatherGPT

A grounded, multilingual, voice-first weather assistant for India: a non-commercial, public-interest website (progressive web app). Three people build it through GitHub, each with their own Antigravity agent: Ashwin (lead), Aman and Pradeep. This repository is the complete starting project: specification, tickets, rules, skills, prompts, seeds, team workflow and GitHub setup. The agents write the code.

## Start
1. **Ashwin, once:** follow `docs/github-setup.md` (create the repo, push this folder, fill `team/members.csv`, run `python scripts/github/bootstrap.py`).
2. **Everyone:** clone the repo, install Docker, Python 3.12, Node.js 20+ and ffmpeg, copy `.env.example` to `.env` and fill in your keys (never paste keys into chat), run `python scripts/dev.py doctor`.
3. In Antigravity, let routine terminal commands run without asking (sandbox on). Paste your kickoff prompt from `team/prompts/<name>.md`. It works autonomously: ticket after ticket, pull requests, CI, self-repair, ledger.
4. If a session stops, paste Prompt B from `docs/antigravity-prompts.md`. Other situational prompts (CI red, merge conflict, review, standup, IMD key arrived, final repair, demo pack) are in the same file.

## What is inside
- `docs/AUTOPILOT.md`: the manual each agent follows. `docs/team.md`: roles, ownership, branches, reviews. `docs/github-setup.md`: one-time GitHub setup.
- `docs/architecture.md`, `docs/integration-notes.md`, `docs/ui-spec.md`, `docs/eval-and-acceptance.md`, `docs/troubleshooting.md`: the references agents read before they act.
- `docs/api-keys.md`, `.env.example`, `docs/ml-plan.md`: keys and models. `docs/adr/`: nine decisions. `GLOSSARY.md`.
- `.scratch/weathergpt/SPEC.md`, `issues/` (22 tickets and `ORDER.md`), `progress/` (one ledger per person; `PROGRESS.md` is generated).
- `AGENTS.md`, `.agents/rules/`, `.agents/skills/`: always-on rules and repeatable procedures.
- `seeds/`: starting prompts, tool definitions, glossary, alert templates, UI strings, example golden cases.
- `team/`: members, assignments, status (IMD key flag), kickoff prompts. `.github/`: CI, templates, CODEOWNERS. `scripts/`: task runner and GitHub bootstrap.

## Human-only steps (agents cannot do these)
- IMD API key: applied for and pending; when it arrives, Ashwin sets `imd_key_available: yes` in `team/status.md` through a pull request and runs Prompt C.
- Keys: Bhashini, and Groq or OpenRouter model IDs in `.env`.
- Native-speaker sign-off for Hindi and every new language; a domain reviewer for advisories; consent and privacy wording.
- Opening pull requests when `gh` is not set up; production deployment approval.
