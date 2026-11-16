---
trigger: always_on
description: Work autonomously, repair your own errors, keep your ledger and use credits sparingly.
---

# Autonomy and credit use

**Decide, don't ask.** When something is unclear, choose the option that follows the spec and the decision records, write the assumption in the pull request and your ledger, and continue. Stop for a human only at human-only steps (keys, native-speaker sign-off, consent wording, IMD terms, production deploy); keep going with stubs or fixtures and mark them.

**Repair your own errors.** When a command or test fails, read the error, check docs/troubleshooting.md, fix the cause, re-run the narrowest check, then the full suite. After three different failed attempts at one failure, write a blocker note (what you tried, the error, your best hypothesis), label the issue status:blocked and take the next ready item. Never delete or loosen a test, skip a gate, or hard-code an answer to get green.

**Prove before you tick.** Tick an acceptance box only with a passing test or command output that shows it.

**Keep the ledger.** After each ticket update your own ledger in .scratch/weathergpt/progress/. At the end of a session write a standup note.

**Spend credits sparingly.** Plans under 15 lines. Reuse what you have read. Focused tests while iterating, the full suite once per ticket. Browser and screenshots only to verify UI at the end of a UI ticket. Notes of ten lines or fewer. Batch related edits. Stop when the ticket is done.
