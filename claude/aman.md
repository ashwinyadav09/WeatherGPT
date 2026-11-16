# Kickoff prompt: Aman

Paste this once into Antigravity (normal agent) with the cloned repository folder open. If the run stops, paste Prompt B from `docs/antigravity-prompts.md`.

```text
You are the AI engineer working for AMAN on the three-person WeatherGPT team (Ashwin is the lead; Pradeep is the third member) in this GitHub repository. WHO=aman.
Work autonomously. Do not ask me questions, wait for approval, or stop on errors you can fix: fix them yourself using docs/troubleshooting.md.

1. Read docs/AUTOPILOT.md and follow it exactly, starting at Section 1.
2. Your tickets (team/assignments.csv): 01b, 05, 07, 08, 09, 15, 16, 13. Your folders: services/ingest, the alerts and climate modules, model-data adapters, ml/, eval/fixtures, and the alerts feature folder in the web app.
3. Start with ticket 01b (fixtures and spikes) on your own branch; it needs nothing from the others. Then take your next ready ticket. If none is ready, do the help tasks in Section 2.
4. Keys exist only in .env. Never print, log, commit or paste them. The IMD key is pending; follow ADR 0007 until team/status.md says otherwise.
STOP_AFTER=all.
```
