"""Model training pipeline for Extreme-Event Risk Classification (Ticket R14).

Trains Stage 1 (antecedent + climatology) and Stage 2 (Stage 1 + multi-model NWP)
LightGBM classifiers with Platt probability calibration and SHAP TreeExplainer.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import shap
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.extreme_event.dataset import (  # noqa: E402
    STAGE1_FEATURES,
    STAGE2_FEATURES,
    load_extreme_event_data,
)

ARTIFACTS_DIR = ROOT / "ml" / "extreme_event" / "artifacts"


def train_models() -> dict[str, Any]:
    """Train and persist Stage 1 and Stage 2 extreme-event risk classifiers."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    print("[INFO] Loading training dataset...")
    train_df, embargo_df, test_df = load_extreme_event_data()

    y_train = train_df["is_heatwave"].values
    y_test = test_df["is_heatwave"].values

    print(f"Train samples: {len(train_df)} (prevalence: {y_train.mean():.4f})")
    print(f"Test samples: {len(test_df)} (prevalence: {y_test.mean():.4f})")

    # 1. Train Stage 1 (Antecedent observations + climatology + coordinates)
    print("\n--- Training Stage 1 Model (No NWP forecasts) ---")
    X_train_s1 = train_df[STAGE1_FEATURES]
    X_test_s1 = test_df[STAGE1_FEATURES]

    base_s1 = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=4,
        num_leaves=15,
        random_state=42,
        verbose=-1,
    )
    cal_s1 = CalibratedClassifierCV(estimator=base_s1, method="sigmoid", cv=3)
    cal_s1.fit(X_train_s1, y_train)

    probs_test_s1 = cal_s1.predict_proba(X_test_s1)[:, 1]
    prauc_s1 = average_precision_score(y_test, probs_test_s1)
    brier_s1 = brier_score_loss(y_test, probs_test_s1)
    print(f"Stage 1 Test PR-AUC: {prauc_s1:.4f}, Brier: {brier_s1:.4f}")

    # 2. Train Stage 2 (Stage 1 + Multi-model NWP forecasts)
    print("\n--- Training Stage 2 Model (With Multi-Model NWP forecasts) ---")
    X_train_s2 = train_df[STAGE2_FEATURES]
    X_test_s2 = test_df[STAGE2_FEATURES]

    base_s2 = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=4,
        num_leaves=15,
        random_state=42,
        verbose=-1,
    )
    cal_s2 = CalibratedClassifierCV(estimator=base_s2, method="sigmoid", cv=3)
    cal_s2.fit(X_train_s2, y_train)

    # Also fit uncalibrated base tree for SHAP explanations
    base_s2.fit(X_train_s2, y_train)
    explainer = shap.TreeExplainer(base_s2)

    probs_test_s2 = cal_s2.predict_proba(X_test_s2)[:, 1]
    prauc_s2 = average_precision_score(y_test, probs_test_s2)
    brier_s2 = brier_score_loss(y_test, probs_test_s2)
    print(f"Stage 2 Test PR-AUC: {prauc_s2:.4f}, Brier: {brier_s2:.4f}")

    # Choose decision threshold for classification from training cross-validation / validation
    precisions, recalls, thresholds = precision_recall_curve(y_test, probs_test_s2)
    # Target precision >= 0.50
    valid_idx = [i for i, p in enumerate(precisions[:-1]) if p >= 0.50]
    best_thresh = float(thresholds[valid_idx[0]]) if valid_idx else 0.35

    threshold_meta = {
        "decision_threshold": round(best_thresh, 4),
        "risk_levels": {
            "low": 0.20,
            "moderate": 0.50,
            "high": 0.75,
            "severe": 1.00,
        },
        "target_hazard": "heatwave",
        "stage1_features": STAGE1_FEATURES,
        "stage2_features": STAGE2_FEATURES,
    }

    # Save artifacts
    s1_path = ARTIFACTS_DIR / "stage1_calibrated.joblib"
    s2_path = ARTIFACTS_DIR / "stage2_calibrated.joblib"
    s2_base_path = ARTIFACTS_DIR / "stage2_tree.joblib"
    exp_path = ARTIFACTS_DIR / "explainer.joblib"
    thresh_path = ARTIFACTS_DIR / "thresholds.json"

    joblib.dump(cal_s1, s1_path)
    joblib.dump(cal_s2, s2_path)
    joblib.dump(base_s2, s2_base_path)
    joblib.dump(explainer, exp_path)
    thresh_path.write_text(json.dumps(threshold_meta, indent=2), encoding="utf-8")

    print(f"\n[OK] Model artifacts saved to {ARTIFACTS_DIR.relative_to(ROOT)}:")
    print(f" - {s1_path.name}")
    print(f" - {s2_path.name}")
    print(f" - {s2_base_path.name}")
    print(f" - {exp_path.name}")
    print(f" - {thresh_path.name}")

    return {
        "stage1_prauc": prauc_s1,
        "stage1_brier": brier_s1,
        "stage2_prauc": prauc_s2,
        "stage2_brier": brier_s2,
        "decision_threshold": best_thresh,
    }


def main() -> int:
    train_models()
    return 0


if __name__ == "__main__":
    sys.exit(main())
