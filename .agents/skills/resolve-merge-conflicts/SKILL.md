---
name: resolve-merge-conflicts
description: Resolve a rebase or merge conflict. Use when git reports conflicts after fetching origin/main.
---

# Resolve merge conflicts

1. `git fetch origin`, then `git rebase origin/main` on your own branch (never rewrite a shared branch).
2. For each conflicted file, read both sides and the commits that changed them; work out what each side intended and keep both intents. Never take one side wholesale without reading the other.
3. Regenerate generated files (lockfiles, openapi.json, PROGRESS.md) instead of merging them by hand. For migrations keep main's head, regenerate yours on top, and check that alembic shows one head.
4. `git add` the files, `git rebase --continue`, then run `python scripts/dev.py ci`.
5. Push with --force-with-lease (own branch only).

If the conflict is in another person's folder, keep their version and re-apply your change through their stub or an issue labelled needs:<owner>.

Done means: the rebase finished, CI is green, and `git grep -n "<<<<<<<"` finds nothing.
