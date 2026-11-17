# Antigravity prompts

Each person pastes their own kickoff prompt once (`team/prompts/ashwin.md`, `aman.md`, `pradeep.md`). Everything else is below. Paste one prompt at a time into the normal Antigravity agent with the repository folder open. Replace <WHO> with your name in lowercase and anything in angle brackets. Keys go in `.env`, never in a prompt.

The manual the prompts rely on is `docs/AUTOPILOT.md`; the failure playbook is `docs/troubleshooting.md`. The normal agent is recommended over /teamwork: each person already has their own agent, it costs fewer credits, and the ledger lets any session resume.

| When | Prompt | Who |
|---|---|---|
| Start | kickoff file in team/prompts | each person, once |
| A session stopped (credits, context) | B | everyone |
| IMD key arrived | C | Ashwin |
| All tickets merged: final repair | D | Ashwin |
| Training tickets 15 and 16 | E | Aman |
| CI is red on my pull request | F | everyone |
| Merge conflict | G | everyone |
| Review comments to address | H | everyone |
| Review a pull request | R | reviewers; authors before asking |
| End-of-day note | S | everyone |
| Stuck on blockers | T | everyone |
| UI polish and accessibility | U | Pradeep |
| Demo, docs and deployment pack (ticket 22) | V | Ashwin |
| Choose the LLM models | X | Ashwin |
| Setup errors on my machine | Y | everyone |

## Prompt B: Resume
```text
Resume WeatherGPT work for <WHO>. Read docs/AUTOPILOT.md and follow it from Section 1: sync main, read my ledger, pick my next ready ticket, and continue. Work autonomously; never ask me questions; fix your own errors. STOP_AFTER=all.
```

## Prompt C: The IMD key has arrived (Ashwin)
```text
The IMD API key is now in my .env as IMD_API_KEY (never print it). Make a small pull request that changes imd_key_available to yes in team/status.md, then work tickets 17 and 18 using the AUTOPILOT.md rules. For each IMD adapter: call the live endpoint and record dated fixtures with provenance=live-recorded; diff them against the documented-sample fixtures and list every difference (field names, types, time zones, colour codes, empty cases) in the ticket; fix the parsers; run the conformance suite on the live fixtures; only then set IMD_ENABLED=true in development. Respect IMD's rate limits and cache responses. Re-run the full suite and the evaluation for every enabled language and record any score change. Then add a comment on issue 19 that it is unblocked for Pradeep. Update my ledger and the standup note.
```

## Prompt D: Final repair and handoff (Ashwin, when every ticket is merged)
```text
Run the final repair pass for WeatherGPT on a branch named fix/final-repair. Run `python scripts/dev.py acceptance`, the evaluation for every enabled language, linters, type checks, accessibility checks and the secret scan. Fix every failure yourself using the self-repair rules. Then review the whole repository along two separate axes and fix what you find: standards (AGENTS.md, the rules, docs/adr, docs/architecture.md) and spec (SPEC.md and every ticket's acceptance boxes). Check specifically: every number comes from an evidence packet, no LLM call sits in the alert path, fixtures carry provenance labels, no secrets in the repository or its history, licence register entries are complete, tests take expected values from fixtures. Write .scratch/weathergpt/HANDOFF.md (what works, what is stubbed, what each human-only step needs, how to run everything), open a pull request, and report only what still needs a human.
```

## Prompt E: Train the two ML models (Aman)
```text
Work ticket 15, then ticket 16, using the AUTOPILOT.md rules. Use only the data sources in docs/ml-plan.md. Make each pipeline reproducible on a laptop CPU and in a free Colab notebook: a dataset manifest (name, date pulled, URL, licence, checksum), a time-based split, evaluation against the baselines named in the ticket, and a model card. Never commit raw data or keys. Wire a model into the product only if it beats its baseline on held-out data; otherwise leave it out and record the result in the ticket. One pull request per ticket.
```

## Prompt F: Fix CI
```text
CI is failing on my pull request (or `python scripts/dev.py ci` fails locally). Use the fix-ci skill: get the failing logs, reproduce locally, find the cause in docs/troubleshooting.md, fix the cause, push and confirm green. Never loosen or delete tests or skip gates. After three different failed attempts, write a blocker note in my ledger and the issue and stop.
```

## Prompt G: Merge conflicts
```text
My branch conflicts with main. Use the resolve-merge-conflicts skill: rebase on origin/main, keep both sides' intent, regenerate generated files and migrations, run `python scripts/dev.py ci`, and push with --force-with-lease to my own branch only. If the conflict is in another person's folder, keep their version and re-apply my change through their stub or an issue labelled needs:<owner>.
```

## Prompt H: Address review comments
```text
Read the review comments on my open pull requests (`gh pr view <n> --comments` and `gh pr diff <n>`). For each comment: fix it, or reply with a short reason if it is wrong, never ignore one. Run `python scripts/dev.py ci`, push, and reply on the pull request. Update my ledger. Do not merge; the reviewer merges.
```

## Prompt R: Review a pull request
```text
Review pull request <n> (or my own branch against origin/main) with the review-pr skill. Report two separate axes: standards (AGENTS.md, the rules, docs/adr, docs/architecture.md) and spec (the ticket's acceptance boxes and nothing more). Run the proofs yourself. List issues only, each with a severity (blocker, should-fix, nit), the evidence and a suggested fix. If I am the requested reviewer, post the review with gh: approve when there are no blockers and CI is green, otherwise request changes.
```

## Prompt S: Standup note
```text
Write my standup note to .scratch/weathergpt/standups/<today>-<WHO>.md from my ledger, my pull requests and the issue list: done, in review, blocked, next, waiting on. Keep it under 15 lines. Update the ledger so it matches. Reply with the five most important lines.
```

## Prompt T: Stuck pass
```text
Take every item in my ledger marked blocked. For each: re-read its blocker note, re-read the relevant section of docs/troubleshooting.md and docs/integration-notes.md, try one new approach (a smaller scope that still meets the acceptance boxes, a different library, a recorded fixture instead of a live call), and re-run the narrowest check. If it works, finish the ticket the normal way. If not, update the note with what you tried and label the issue needs:ashwin. Never loosen a test or skip a gate.
```

## Prompt U: UI polish and accessibility (Pradeep)
```text
Run a UI pass on the whole website against docs/ui-spec.md. Check every page and state (loading, partial, offline, error, permission denied), the English and Hindi text, the tokens and the alert colours, keyboard-only use of the main flows, the automated axe checks, Lighthouse performance and PWA scores, and the performance budget. Fix what fails, add tests for each fix, and save the Lighthouse and axe reports under eval/results. One pull request.
```

## Prompt V: Demo, docs and deployment pack (Ashwin, ticket 22)
```text
Work ticket 22 using the AUTOPILOT.md rules. Seed demo data and script the demo from docs/eval-and-acceptance.md; write the developer README, an architecture diagram (mermaid) and a runbook; write the deployment guide and scripts for one India-region VM (Compose production profile with Caddy TLS, backups, environment checklist) without deploying anything; make `python scripts/dev.py acceptance` print a pass or fail table for every gate and store the output; and write .scratch/weathergpt/HANDOFF.md.
```

## Prompt X: Choose the LLM models (Ashwin, after ticket 02 merges)
```text
Run the model selection step from docs/integration-notes.md. Using the OpenRouter and Groq keys in my .env, list candidate models that support tool calling, run the tool-call golden cases (at least 30 English and 30 Hindi) on up to three candidates for the main role and up to three for the fast role, record accuracy, latency and cost per case, pick the cheapest that meets the thresholds in docs/eval-and-acceptance.md, and write the choice and reasons to config/models.yaml. Never print keys. Open a pull request and add the result to ticket 02's issue.
```

## Prompt Y: Fix my setup
```text
Run `python scripts/dev.py doctor`. For each missing or failing item, fix it if you can on this machine (install the tool, start Docker, copy .env.example to .env), using docs/troubleshooting.md; if it needs me (installing Docker Desktop, signing in to gh, adding keys to .env), write it in SETUP_NEEDED.md in plain steps. Run doctor again and report what is left.
```
