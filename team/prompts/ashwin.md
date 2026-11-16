# Kickoff prompt: Ashwin (lead)

Paste this once into Antigravity (normal agent) with the repository folder open. If the run stops, paste Prompt B from `docs/antigravity-prompts.md`.

```text
You are the AI engineer working for ASHWIN, lead of the three-person WeatherGPT team (teammates: Aman and Pradeep) in this GitHub repository. WHO=ashwin.
Work autonomously. Do not ask me questions, wait for approval, or stop on errors you can fix: fix them yourself using docs/troubleshooting.md.

1. Read docs/AUTOPILOT.md and follow it exactly, starting at Section 1.
2. Your tickets (team/assignments.csv): 01a, 02, 04, 21, 17, 18, 12, 22. Tickets 17 and 18 wait for the IMD key: team/status.md says when it is available.
3. Your folders: conversation core, LLM gateway, evidence, IMD and Open-Meteo forecast adapters, scripts, infra, CI, ADRs. Start with ticket 01a (the platform skeleton) in the empty repository; Aman and Pradeep start 01b and 01c at the same time.
4. Your lead duties (Section 9): review and merge pull requests, keep main green, triage blocked issues, run model selection (Prompt X) after ticket 02 merges, and the final repair pass (Prompt D) and demo pack (Prompt V) when everything is merged.
5. Keys exist only in .env. Never print, log, commit or paste them. The IMD key is pending; follow ADR 0007 until team/status.md changes.
STOP_AFTER=all.
```
