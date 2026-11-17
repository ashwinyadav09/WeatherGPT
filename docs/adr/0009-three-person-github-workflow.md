# 0009: Three-person GitHub workflow

**Status:** accepted (15 November 2026)

**Context:** Ashwin (lead), Aman and Pradeep each work with their own AI agent in one GitHub repository. Parallel agents collide on shared files unless the structure prevents it.

**Decision:** Work is split into three lanes by folder ownership (docs/team.md, CODEOWNERS). Tickets become GitHub issues with owners, reviewers and blocking links, created by scripts/github/bootstrap.py. Each ticket is one branch and one pull request into a protected main with one human approval and a green CI check. Shared shapes live in packages/contracts and change through labelled pull requests. Modules, adapters and web features register through extension points so adding one never edits a shared file. Each person edits only their own progress ledger; PROGRESS.md is generated. Ashwin holds the IMD key and merges contracts and migrations.

**Consequences:** Agents can work in parallel with few conflicts and resume from the ledger. Waiting is handled by help tasks. If branch protection is unavailable, the same rules hold by convention.
