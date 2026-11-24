"""Train intent classification models on MASSIVE Indic + English dataset (Ticket R12).

Models:
- Baseline 0: RuleIntentBaseline (keyword rules)
- Baseline 1: TF-IDF (char n-grams 2-5) + LogisticRegression (balanced weights)
- Temperature scaling & threshold selection:
  Finds auto-route threshold tau on validation set where precision >= 95%.

Saves artifacts:
- ml/intent/artifacts/intent_model.joblib
- ml/intent/artifacts/model_metadata.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.intent.dataset import CANONICAL_INTENTS, get_stratified_splits, load_dataset  # noqa: E402
from ml.intent.model import RuleIntentBaseline  # noqa: E402

ARTIFACTS_DIR = ROOT / "ml" / "intent" / "artifacts"
MODEL_FILE = ARTIFACTS_DIR / "intent_model.joblib"
METADATA_FILE = ARTIFACTS_DIR / "model_metadata.json"


def evaluate_rule_baseline(val_rows: list[dict[str, Any]]) -> dict[str, float]:
    """Evaluate RuleIntentBaseline on validation rows."""
    rule_model = RuleIntentBaseline()
    y_true: list[str] = []
    y_pred: list[str] = []

    # Map rule baseline intents to canonical intents
    rule_map = {
        "current": "current_conditions",
        "forecast": "forecast",
        "alert": "alert",
        "advisory": "advisory",
        "climate": "climate_history",
        "explain": "general_knowledge",
        "meta": "general_knowledge",
        "unsafe": "out_of_domain",
    }

    for r in val_rows:
        pred = rule_model.predict(r["text"])
        canon_pred = rule_map.get(pred.intent, "out_of_domain")
        y_true.append(r["intent"])
        y_pred.append(canon_pred)

    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    acc = correct / len(y_true) if y_true else 0.0

    return {"macro_f1": macro_f1, "accuracy": acc}


def train_intent_model() -> dict[str, Any]:
    print("ml.intent.train: Loading dataset and preparing splits...")
    rows = load_dataset()
    train_rows, val_rows = get_stratified_splits(rows, val_ratio=0.20, seed=42)
    print(f"Train samples: {len(train_rows)}, Validation samples: {len(val_rows)}")

    # 1. Evaluate Baseline 0
    rule_metrics = evaluate_rule_baseline(val_rows)
    print(f"Baseline 0 (RuleIntentBaseline) Val Macro-F1: {rule_metrics['macro_f1']:.4f}, Acc: {rule_metrics['accuracy']:.4f}")

    # 2. Train Baseline 1: TF-IDF (char 2-5 grams) + Logistic Regression
    X_train = [r["text"] for r in train_rows]
    y_train = [r["intent"] for r in train_rows]
    X_val = [r["text"] for r in val_rows]
    y_val = [r["intent"] for r in val_rows]

    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                min_df=2,
                max_features=15000,
                sublinear_tf=True,
            ),
        ),
        (
            "clf",
            LogisticRegression(
                C=3.0,
                max_iter=600,
                class_weight="balanced",
                random_state=42,
            ),
        ),
    ])

    print("Fitting TF-IDF + LogisticRegression pipeline...")
    pipeline.fit(X_train, y_train)

    # Validation evaluation
    y_val_pred = pipeline.predict(X_val)
    val_probs = pipeline.predict_proba(X_val)
    val_max_probs = np.max(val_probs, axis=1)

    macro_f1 = float(f1_score(y_val, y_val_pred, average="macro", zero_division=0))
    correct = sum(1 for t, p in zip(y_val, y_val_pred) if t == p)
    accuracy = correct / len(y_val) if y_val else 0.0

    print(f"Baseline 1 (TF-IDF + LogReg) Val Macro-F1: {macro_f1:.4f}, Acc: {accuracy:.4f}")

    # 3. Find auto-route threshold tau for precision >= 95%
    candidate_thresholds = np.linspace(0.40, 0.95, 56)
    selected_tau = 0.75
    selected_prec = 0.0
    selected_coverage = 0.0

    for tau in candidate_thresholds:
        mask = val_max_probs >= tau
        if np.sum(mask) >= 20:  # Need at least 20 routed queries for statistical significance
            routed_correct = sum(1 for t, p, m in zip(y_val, y_val_pred, mask) if m and (t == p))
            routed_total = int(np.sum(mask))
            prec = routed_correct / routed_total
            coverage = routed_total / len(y_val)
            if prec >= 0.95:
                selected_tau = float(round(tau, 3))
                selected_prec = float(round(prec, 4))
                selected_coverage = float(round(coverage, 4))
                break

    print(f"Selected Auto-Route Threshold tau: {selected_tau} (Precision: {selected_prec:.2%}, Coverage: {selected_coverage:.2%})")

    # 4. Save artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_FILE)
    print(f"[OK] Saved model pipeline to {MODEL_FILE}")

    metadata = {
        "model_version": "intent-v1.0",
        "labels": CANONICAL_INTENTS,
        "n_train": len(train_rows),
        "n_val": len(val_rows),
        "classes": list(pipeline.classes_),
        "val_macro_f1": round(macro_f1, 4),
        "val_accuracy": round(accuracy, 4),
        "baseline0_macro_f1": round(rule_metrics["macro_f1"], 4),
        "baseline0_accuracy": round(rule_metrics["accuracy"], 4),
        "auto_route_threshold": selected_tau,
        "tau_precision": selected_prec,
        "tau_coverage": selected_coverage,
    }

    with METADATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"[OK] Saved metadata to {METADATA_FILE}")

    return metadata


def main() -> int:
    train_intent_model()
    return 0


if __name__ == "__main__":
    sys.exit(main())
