# BLOCKED: Phase R12 (Intent and Slot Model)

## Status: BLOCKED_PENDING_H1
**Ticket:** R12 (Intent and slot model)
**Timestamp:** 2026-11-24T14:01:09.105108+00:00
**Git SHA:** `2df9bd6e4202356c68f856c9bbfe2d3c91ed50b6`

## What Was Attempted
1. Downloaded real Amazon MASSIVE 1.1 dataset (16,521 utterances each for English, Hindi, Bengali, Tamil, Telugu; total 82,605 real human utterances) and unpacked to `ml/intent/data/raw/massive/`.
2. Built processed training dataset with 4,842 rows across 5 languages, each tagged with its `source` (`'massive'` or `'human_seed'`).
3. Trained Baseline 0 (`RuleIntentBaseline`) and Baseline 1 (TF-IDF char n-grams 2-5 + calibrated `LogisticRegression`), achieving Validation Macro-F1 = 0.6296 and Accuracy = 0.7919 on held-out validation samples. Selected auto-route threshold $\tau = 0.68$ (achieving 95.43% precision on validation data).
4. Saved trained pipeline to `ml/intent/artifacts/intent_model.joblib`.
5. Created H1 gold set template at `seeds/eval/intent_gold_template.json` and loader at `eval/intent/gold_set_loader.py`.

## Reason for Block
Per Rule S1 and Table 2 (Human-only steps H1):
- **Missing Human Input:** 350 human-written and verified test queries (50 per Tier-1 language: English, Hindi, Bengali, Marathi, Telugu, Tamil, Odia) with intent and slot annotations.
- Native or fluent speakers must verify queries in each language.
- Under Rule T1, T2, and T3, artificial test sets are strictly forbidden; evaluation metrics cannot be hand-typed or estimated.

## What Humans Must Provide
Human contributors must populate `eval/intent/gold_test_set.json` conforming to `seeds/eval/intent_gold_template.json` with 50 verified queries per language across all 7 Tier-1 languages.
Once provided, running `python ml/intent/eval.py` will automatically test the model on the gold set and generate headline test metrics.
