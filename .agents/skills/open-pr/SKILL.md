---
name: open-pr
description: Open a pull request for a finished ticket. Use when a ticket branch passes CI locally.
---

# Open a pull request

1. Confirm git status is clean, the branch is rebased on origin/main, and `python scripts/dev.py ci` passed.
2. Push: `git push -u origin <branch>` (use --force-with-lease only after rebasing your own branch).
3. Fill .github/PULL_REQUEST_TEMPLATE.md: ticket and issue number, what changed, each acceptance box with its proof, the checks, assumptions.
4. Create it: `gh pr create --base main --title "<NN>: <title>" --body-file <file> --reviewer <reviewer from team/assignments.csv>`. Add the label contract if packages/contracts changed.
5. Set the issue to status:in-review and note the PR number in your ledger.

If gh is unavailable, save the body to .scratch/weathergpt/pr/<branch>.md and list the step as human-only.

Done means: the PR exists (or the body is saved), the reviewer is requested, the ledger says in-review.
