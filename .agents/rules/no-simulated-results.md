---
trigger: always_on
description: Strictest truthfulness rules. Never hard-code, simulate or hand-type a measured result. If real data is not available, stop and mark blocked.
---

# No-simulated-results rules (V3)

## Truthfulness
- **T1. No simulated results.** Never hard-code, simulate, estimate or hand-type a metric, latency, accuracy, uptime, count or score. Every reported number comes from a script that reads real inputs and writes a result file.
- **T2. Not measured is a valid value.** Write `NOT MEASURED`. Acceptance fails in strict mode if a result is missing.
- **T3. Synthetic data is allowed only inside unit tests,** and never for training, validation, testing or any reported number. LLM-generated or machine-translated training text is allowed only if labelled in a `source` column and never in a test set.
- **T4. Reports are generated.** `MODEL_CARD.md`, `EVAL_REPORT.md` and `docs/EVAL_RESULTS.md` are rendered from result files; the renderer fails on a missing value.
- **T5. Never add a check that requires a metric to be nonzero, below 100%, or inside a "plausible" range.** A perfect or zero result is reported as it is and flagged for human review.
- **T6. Name the real source.** Provenance values are only `live_api`, `recorded_real_http`, `real_audio`, `human_labels`, `fixture_test_only`. `fixture_test_only` may never appear in a performance claim.
- **T7. No stub in any path that produces a result or user-visible content.** Stub adapters exist for tests and are injected explicitly. A missing provider raises `ProviderNotConfigured`.
- **T8. IMD is out of scope.** Dormant adapters remain behind the existing flag.

## Stop conditions (S)
- **S1.** If a real data download fails, a dataset is too small (thresholds are in each ticket), or a human-provided input is missing, stop the ticket. Write `BLOCKED.md` (what was tried, the exact error, what a human must provide), set the ledger status to `blocked`, and continue with the next ticket.
- **S2.** If a model does not beat its baseline, ship the baseline, keep `enabled=false` for the model, and report the negative result in the model card.
- **S3.** Test sets are touched once. Log every evaluation of a test set in `RUN_MANIFEST.json`; a second evaluation after changes needs a new test block or a note explaining why.

## Guard protection (G)
- **G1.** Add `.github/CODEOWNERS` so that changes to `services/api/tests/guards/**`, `ml/common/**`, `scripts/tasks/audit_results.py`, `.agents/rules/**` and `CODEOWNERS` require review by Ashwin. Do not weaken, skip or rewrite those files in the same PR as the code they check.
