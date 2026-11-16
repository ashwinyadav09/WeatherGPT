---
name: fix-ci
description: Repair a failing CI run or a failing local ci. Use when checks fail on a pull request or when `python scripts/dev.py ci` exits non-zero.
---

# Fix CI

1. Get the failure: `gh pr checks` and `gh run view <id> --log-failed`; locally, read the dev.py ci output.
2. Reproduce locally the same way: clean container, TZ=UTC, recorded fixtures only.
3. Find the row in docs/troubleshooting.md and fix the cause, not the symptom. Never delete or loosen a test, skip a gate, or mock inside the process.
4. Re-run the narrowest failing check, then `python scripts/dev.py ci`.
5. Commit `<NN>: fix ci (<what>)`, push, and confirm the run is green.

After three different failed attempts, write a blocker note and label the issue status:blocked.

Done means: CI is green on GitHub for the latest commit.
