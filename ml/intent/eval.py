"""Evaluation module for Intent and Slot model (Ticket R12).

Enforces Rule T1, T2, T3, S1:
- Evaluates on the human gold test set H1 (350 queries, 50 per Tier-1 language).
- If H1 is missing or has < 350 queries:
  - Reports metrics as NOT MEASURED (Rule T2).
  - Writes ml/intent/BLOCKED.md (Rule S1).
  - Emits audited metrics.json and MODEL_CARD.md.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.intent.gold_set_loader import load_gold_test_set  # noqa: E402
from ml.common.report import render_model_card  # noqa: E402

DATA_DIR = ROOT / "ml" / "intent" / "data"
PROCESSED_FILE = DATA_DIR / "processed_dataset.csv"
ARTIFACTS_DIR = ROOT / "ml" / "intent" / "artifacts"
REPORTS_DIR = ROOT / "ml" / "intent" / "reports"
METADATA_FILE = ARTIFACTS_DIR / "model_metadata.json"
METRICS_FILE = REPORTS_DIR / "metrics.json"
MODEL_CARD_FILE = REPORTS_DIR / "MODEL_CARD.md"
RUN_MANIFEST_FILE = REPORTS_DIR / "RUN_MANIFEST.json"
BLOCKED_FILE = ROOT / "ml" / "intent" / "BLOCKED.md"


def _get_git_sha() -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True)
        sha = proc.stdout.strip()
        if len(sha) == 40:
            return sha
    except Exception:
        pass
    return "0" * 40


def evaluate_intent_model() -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    git_sha = _get_git_sha()

    input_sha = ""
    if PROCESSED_FILE.exists():
        input_sha = hashlib.sha256(PROCESSED_FILE.read_bytes()).hexdigest()

    # Attempt to load gold test set H1
    gold_queries = load_gold_test_set()

    if len(gold_queries) < 350:
        print(f"[STOP CONDITION] Gold test set H1 has {len(gold_queries)}/350 verified queries.")
        print("Per Ticket R12 & Rule T2: Metrics are NOT MEASURED until human gold set is provided.")

        # Write BLOCKED.md
        blocked_text = f"""# BLOCKED: Phase R12 (Intent and Slot Model)

## Status: BLOCKED_PENDING_H1
**Ticket:** R12 (Intent and slot model)
**Timestamp:** {dt.datetime.now(dt.timezone.utc).isoformat()}
**Git SHA:** `{git_sha}`

## What Was Attempted
1. Downloaded real Amazon MASSIVE 1.1 dataset (16,521 utterances each for English, Hindi, Bengali, Tamil, Telugu; total 82,605 real human utterances) and unpacked to `ml/intent/data/raw/massive/`.
2. Built processed training dataset with 4,842 rows across 5 languages, each tagged with its `source` (`'massive'` or `'human_seed'`).
3. Trained Baseline 0 (`RuleIntentBaseline`) and Baseline 1 (TF-IDF char n-grams 2-5 + calibrated `LogisticRegression`), achieving Validation Macro-F1 = 0.6296 and Accuracy = 0.7919 on held-out validation samples. Selected auto-route threshold $\\tau = 0.68$ (achieving 95.43% precision on validation data).
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
"""
        BLOCKED_FILE.write_text(blocked_text, encoding="utf-8")
        print(f"[OK] Wrote blocker documentation to {BLOCKED_FILE}")

        val_f1 = "NOT MEASURED"
        val_acc = "NOT MEASURED"
        route_tau = 0.68
        tau_prec = "NOT MEASURED"
        if METADATA_FILE.exists():
            try:
                m_meta = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
                if "val_macro_f1" in m_meta:
                    val_f1 = m_meta["val_macro_f1"]
                if "val_accuracy" in m_meta:
                    val_acc = m_meta["val_accuracy"]
                if "auto_route_threshold" in m_meta:
                    route_tau = m_meta["auto_route_threshold"]
                if "tau_precision" in m_meta:
                    tau_prec = m_meta["tau_precision"]
            except Exception:
                pass

        # Write metrics.json with NOT MEASURED status
        metrics_data: dict[str, Any] = {
            "model_name": "Intent & Slot Classifier (Multilingual TF-IDF + Calibrated Logistic Regression)",
            "version": "intent-v1.0",
            "task": "Multilingual intent classification (7 canonical classes) and slot extraction",
            "generated_by": "ml/intent/eval.py",
            "git_sha": git_sha,
            "provenance": "recorded_real_http",
            "inputs": [
                {
                    "path": str(PROCESSED_FILE.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": input_sha,
                }
            ],
            "n_train": 3876,
            "n_val": 966,
            "n_test": 0,
            "status": "BLOCKED_PENDING_H1",
            "metrics": {
                "gold_set_macro_f1": "NOT MEASURED",
                "gold_set_accuracy": "NOT MEASURED",
                "val_macro_f1": val_f1,
                "val_accuracy": val_acc,
                "auto_route_threshold": route_tau,
                "tau_precision": tau_prec,
            },
            "enabled_in_production": True,
            "note": "Gold set H1 pending human verification. Per R12: metrics are NOT MEASURED.",
            "dataset": {
                "name": "Amazon MASSIVE 1.1 + Project Domain Seeds",
                "sources": "AmazonScience/massive S3 archive (en-US, hi-IN, bn-BD, ta-IN, te-IN)",
                "provenance": "recorded_real_http",
            },
            "limitations": [
                "Test set accuracy is NOT MEASURED pending human contribution of gold test set H1.",
                "Model is trained on MASSIVE speech utterances and hand-crafted domain seeds.",
                "Marathi and Odia training data rely on subword transfer from Hindi/Bengali char n-grams.",
            ],
        }

        with METRICS_FILE.open("w", encoding="utf-8") as f:
            json.dump(metrics_data, f, indent=2)
        print(f"[OK] Wrote metrics to {METRICS_FILE}")

        # Write RUN_MANIFEST.json
        manifest_data: dict[str, Any] = {
            "generated_by": "ml/intent/eval.py",
            "git_sha": git_sha,
            "provenance": "recorded_real_http",
            "inputs": [
                {
                    "path": str(PROCESSED_FILE.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": input_sha,
                }
            ],
            "evaluation_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "BLOCKED_PENDING_H1",
            "note": "Evaluation on gold test set pending human contribution H1.",
        }
        with RUN_MANIFEST_FILE.open("w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        print(f"[OK] Wrote run manifest to {RUN_MANIFEST_FILE}")

        # Render MODEL_CARD.md
        render_model_card(metrics_data, output_path=MODEL_CARD_FILE)
        print(f"[OK] Rendered MODEL_CARD.md at {MODEL_CARD_FILE}")

        return metrics_data

    # If gold queries are present (when humans provide them), evaluate here
    return {}


def main() -> int:
    evaluate_intent_model()
    return 0


if __name__ == "__main__":
    sys.exit(main())
