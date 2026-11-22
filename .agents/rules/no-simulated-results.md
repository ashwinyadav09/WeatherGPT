---
trigger: always_on
description: Every reported number must come from a script that writes a machine-readable result file. Never hard-code, simulate or hand-type a measured result.
---

# No-simulated-results rules (R0.1)

1. **No simulated results.** Never hard-code, simulate, estimate or hand-type a metric, latency, accuracy, uptime or count in code, config or docs. Every reported number must come from a script in the repository that writes a machine-readable result file.
2. **Not measured is a valid value.** If something has not been measured, write `NOT MEASURED`. The acceptance script must fail in strict mode when a result file is missing.
3. **Synthetic data only in unit tests.** Synthetic or LLM-generated data may be used for training only if labelled as such in the model card and never for the reported test set. Test sets are real, held-out, and checked for overlap with training data.
4. **Reports are generated, not written.** `MODEL_CARD.md` and `EVAL_REPORT.md` are rendered by a script from `reports/metrics.json`. The renderer raises an error if a placeholder has no value.
5. **Run manifest on every run.** Each training and evaluation run writes `git_sha`, timestamp, seed, data source URLs, retrieval time, row counts, file checksums and the exact split dates.
6. **Provenance is visible.** Every evidence packet carries `provenance: live | cached | fixture`. Fixture or sample data is never shown to users as an official advisory or alert.
7. **Name the source that really answered.** For example "Open-Meteo (global model)" or "NDMA SACHET". Do not add disclaimers about services that are not part of the product.
8. **IMD is out of scope.** It is not a dependency. Its adapters stay dormant behind the existing flag (ADR 0007). No ticket, test, UI string or report may require it.
9. **No hidden fallbacks to fake data.** If a provider is not configured, raise `ProviderNotConfigured` and show an honest error. Stubs are injected only by tests.
10. **Negative results are results.** If a model does not beat its baseline, ship the baseline and report it.
