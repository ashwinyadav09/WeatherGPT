# Team workflow

Three people build WeatherGPT in one GitHub repository, each with their own Antigravity agent: Ashwin (lead and integrator), Aman (data, alerts, climate, ML) and Pradeep (web, voice, languages). The assignments are in `team/assignments.csv`; the work order is in `.scratch/weathergpt/issues/ORDER.md`.

## Lanes and ownership
| Person | Lane | Owns |
|---|---|---|
| Ashwin | Core and integration | conversation, LLM gateway, evidence, IMD and Open-Meteo forecast adapters, scripts, infra, CI, ADRs, reviews and merges, the IMD key |
| Aman | Data, alerts, climate, ML | ingest worker, alerts (and the alerts feature folder in the web app), model-data adapters, climate, ML training, fixtures, status showcase |
| Pradeep | Web, voice, languages | the web app, places, speech gateway, advisories, i18n, PWA, UI |

Ownership is by folder (see `.github/CODEOWNERS`). You may edit another person's folder only through a pull request that the owner reviews, after opening an issue labelled `needs:<owner>`. Use a stub or a mock at the seam until it lands.

## Extension points (so parallel work does not collide)
- Back-end routers are discovered from each module's `router.py`; adapters register from `config/sources.yaml`. Adding a module never edits a shared file.
- Web pages are features: `apps/web/src/features/<feature>/` with its own routes file and its own translation namespace. A feature never edits another feature's files.
- Shared shapes live in `packages/contracts/`. A change there needs the label `contract` and approval from everyone who consumes it.

## Branches, commits, pull requests
- `main` is protected and always green. Nobody pushes to it.
- One ticket per branch: `ticket/<NN>-<slug>` (for example `ticket/05-alerts-v1`). Fix branches: `fix/<slug>`.
- Commit often in small steps: `<NN>: what changed`. Rebase on `origin/main` before opening the pull request and again before merging. Force-push only your own branch, with `--force-with-lease`.
- A pull request is one ticket, ideally under 400 changed lines apart from generated files, uses the template, links the issue (`Closes #N`) and lists each acceptance box with its proof.
- Run `python scripts/dev.py ci` locally first. CI on GitHub must pass.

## Reviews and merging
- One human approval plus green CI. The reviewer is in `team/assignments.csv`; Ashwin reviews everything that touches shared areas.
- Run the review prompt (Prompt R) before asking a human: it checks standards and spec separately.
- Review within one working day. Squash-merge. The author deletes the branch.
- Ashwin merges migrations and contract changes.

## Migrations
Keep exactly one Alembic head. Before opening a pull request with a migration: `git fetch`, rebase on `origin/main`, run `alembic heads`; if there are two heads, regenerate your migration on top of main's head. CI checks the head count.

## Keys and secrets
- Every person keeps their own `.env` (copied from `.env.example`); `.env` is never committed or pasted into chat.
- The IMD key is held by Ashwin. Share it only if IMD's terms allow shared use, through a password manager, never through the repository or chat. Otherwise each person applies for their own.
- Groq, OpenRouter and Bhashini keys: each person uses their own where possible.
- CI needs no keys. The weekly contract-check workflow uses GitHub Actions secrets that Ashwin sets.
- If a key is committed: rotate it at once, then tell Ashwin. Removing it from history is not enough.

## Daily rhythm
1. Start: `git fetch`, pull `main`, run the resume prompt (Prompt B). The agent reads the ledger and the issue list.
2. Work: take your next ready ticket (blockers merged, not waiting on a key).
3. End: push branches, run the standup prompt (Prompt S), post the note in the team chat or as an issue comment.
4. Ashwin triages every issue labelled `status:blocked` once a day.

## When blocked or idle
If your next ticket is not ready, do these in order: review pull requests assigned to you; fix CI on your own pull requests; do pre-work for your next ticket that needs no blockers (contracts, mocks, tests first, fixtures); improve tests and docs for merged tickets in your area; then stop and post what you are waiting for.

## Credits
Each person has their own Antigravity quota. Use the chunked prompts (STOP_AFTER) to spread credits, do not duplicate work (check the issue assignee and open pull requests first), and keep plans short.

## Definition of ready
Blockers merged; acceptance boxes clear; keys or fixtures available (or the step is marked human-only).

## Definition of done
Merged to main; CI green; acceptance boxes ticked with proof; review note in the issue; ledger updated; docs, glossary or ADR updated if a decision or term changed.
