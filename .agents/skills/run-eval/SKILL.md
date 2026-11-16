---
name: run-eval
description: Run the golden-set evaluation and compare with baseline. Use before merging any change to the agent, prompts, adapters, glossary or models.
---

# Run the evaluation

1. Run `python scripts/dev.py eval --lang <code>` for each affected language.
2. Compare each metric with the stored baseline.
3. List every regression with the failing cases.
4. Fail the change when groundedness is under 99 percent, intent and slot accuracy is under 95 percent, or any metric drops against baseline.
5. Save the report under the eval results folder with the date and model identifiers.

Done means: a report with pass or fail per gate, and any regression explained.
