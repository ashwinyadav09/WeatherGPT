---
name: review-pr
description: Review a pull request along two separate axes, standards and spec. Use before asking a human, and when you are the requested reviewer.
---

# Review a pull request

1. Read it: `gh pr view <n> --json title,body,files` and `gh pr diff <n>` (or `git diff origin/main...HEAD` for your own branch).
2. Standards axis: does it follow AGENTS.md, the rules, docs/adr and docs/architecture.md? Look for numbers not taken from evidence packets, an LLM call in the alert path, fixtures without provenance labels, secrets, missing licence entries, tests that copy expected values from code, edits in other people's folders, hand-edited shared registries, two Alembic heads.
3. Spec axis: does it satisfy the ticket's acceptance boxes and nothing more? Run the proofs yourself.
4. Report issues only, each with a severity (blocker, should-fix, nit), the evidence and a suggested fix. As reviewer, post with `gh pr review <n> --comment`, or `--approve` when there are no blockers and CI is green, or `--request-changes` otherwise.

Done means: both axes are reported and, as reviewer, a review is posted.
