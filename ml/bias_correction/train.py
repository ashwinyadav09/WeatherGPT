"""Train point-forecast bias correction models on real observations (Ticket R20.6 / ADR 0011).

Trains:
- Temperature MOS Ridge Regression (minimizes MAE / RMSE on residual delta)
- Temperature LightGBM Regressor (non-linear gradient boosting on residual delta)
- Quantile Regression (p10, p90) for prediction intervals via LightGBM and empirical residual bounds
- Calibrated probability of precipitation occurrence (>= 2.5 mm) via Logistic Regression & LightGBM

Saves real artifacts to:
- ml/bias_correction/artifacts/ridge_model.joblib
- ml/bias_correction/artifacts/lgbm_model.joblib
- ml/bias_correction/artifacts/model_artifacts.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.linear_model import LogisticRegression, Ridge

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.bias_correction.dataset import (  # noqa: E402
    TRAIN_END_DATE,
    TRAIN_START_DATE,
    VAL_END_DATE,
    VAL_START_DATE,
    get_three_way_splits,
    load_dataset,
)

ARTIFACTS_DIR = ROOT / "ml" / "bias_correction" / "artifacts"
RIDGE_MODEL_FILE = ARTIFACTS_DIR / "ridge_model.joblib"
LGBM_MODEL_FILE = ARTIFACTS_DIR / "lgbm_model.joblib"
ARTIFACTS_JSON_FILE = ARTIFACTS_DIR / "model_artifacts.json"
LEGACY_WEIGHTS_FILE = ARTIFACTS_DIR / "model_weights.json"

TEMP_FEATURE_COLS = [
    "lead_day",
    "tmax_gfs",
    "tmax_ecmwf",
    "tmax_icon",
    "tmax_mmm",
    "doy_sin",
    "doy_cos",
    "lat",
    "lon",
    "elev",
    "recent_bias",
    "trailing_30d_bias",
    "persistence_tmax",
]

RAIN_FEATURE_COLS = [
    "lead_day",
    "rain_mmm",
    "log_rain_mmm",
    "rain_gfs",
    "rain_ecmwf",
    "rain_icon",
    "is_monsoon",
    "lat",
    "lon",
    "elev",
]


def _extract_temp_features(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract design matrix X, raw MMM baseline, and target observed Tmax."""
    x_list = []
    raw_list = []
    y_list = []

    for r in rows:
        lead = float(r["lead_day"])
        gfs = float(r["tmax_gfs"])
        ecmwf = float(r["tmax_ecmwf"])
        icon = float(r["tmax_icon"])
        mmm = float(r["tmax_mmm"])
        doy_s = float(r["doy_sin"])
        doy_c = float(r["doy_cos"])
        lat = float(r["lat"]) / 10.0
        lon = float(r["lon"]) / 10.0
        elev = float(r["elev"]) / 1000.0
        rec_bias = float(r["recent_bias"])
        trail_bias = float(r["trailing_30d_bias"])
        persist = float(r["persistence_tmax"])

        feat = [
            lead,
            gfs,
            ecmwf,
            icon,
            mmm,
            doy_s,
            doy_c,
            lat,
            lon,
            elev,
            rec_bias,
            trail_bias,
            persist,
        ]
        x_list.append(feat)
        raw_list.append(mmm)
        y_list.append(float(r["observed_tmax"]))

    return np.array(x_list, dtype=float), np.array(raw_list, dtype=float), np.array(y_list, dtype=float)


def _extract_rain_features(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    """Extract design matrix X and target y for rain occurrence models."""
    x_list = []
    y_list = []

    for r in rows:
        lead = float(r["lead_day"])
        rain_mmm = max(0.0, float(r["rain_mmm"]))
        log_rain = math.log1p(rain_mmm)
        gfs_rain = max(0.0, float(r["rain_gfs"]))
        ecm_rain = max(0.0, float(r["rain_ecmwf"]))
        icon_rain = max(0.0, float(r["rain_icon"]))
        d = r["date"]
        month = int(d.split("-")[1])
        is_monsoon = 1.0 if 6 <= month <= 9 else 0.0
        lat = float(r["lat"]) / 10.0
        lon = float(r["lon"]) / 10.0
        elev = float(r["elev"]) / 1000.0

        feat = [lead, rain_mmm, log_rain, gfs_rain, ecm_rain, icon_rain, is_monsoon, lat, lon, elev]
        x_list.append(feat)
        y_list.append(int(r["observed_rain_event"]))

    return np.array(x_list, dtype=float), np.array(y_list, dtype=int)


def train_models() -> dict[str, Any]:
    """Train Ridge and LightGBM models on real training data and tune on validation split."""
    print("ml.bias_correction.train: Loading processed dataset...")
    rows = load_dataset()
    train_rows, val_rows, test_rows = get_three_way_splits(rows)

    print(
        f"Splits: {len(train_rows)} train ({TRAIN_START_DATE}..{TRAIN_END_DATE}), "
        f"{len(val_rows)} val ({VAL_START_DATE}..{VAL_END_DATE}), "
        f"{len(test_rows)} held-out test (7-day embargo)."
    )
    if not train_rows:
        raise ValueError("Training set is empty; run 'python scripts/dev.py ml download bias_correction' first.")

    # 1. Temperature Features
    X_temp_train, raw_train, y_temp_train = _extract_temp_features(train_rows)
    delta_train = y_temp_train - raw_train

    X_temp_val, raw_val, y_temp_val = _extract_temp_features(val_rows)

    # 2. Train Ridge Regressor on Delta
    print(f"Fitting Temperature Ridge Regressor on {len(train_rows)} samples...")
    ridge = Ridge(alpha=100.0)
    ridge.fit(X_temp_train, delta_train)
    val_pred_ridge = raw_val + ridge.predict(X_temp_val)
    val_mae_ridge = float(np.mean(np.abs(val_pred_ridge - y_temp_val)))

    # Compute empirical residual bounds on validation set for Ridge p10 and p90
    val_residuals = y_temp_val - val_pred_ridge
    p10_offset = float(np.percentile(val_residuals, 10))
    p90_offset = float(np.percentile(val_residuals, 90))

    # 3. Train LightGBM Regressor on Delta
    print(f"Fitting Temperature LightGBM Regressor on {len(train_rows)} samples...")
    lgb_temp = LGBMRegressor(
        n_estimators=60,
        learning_rate=3 / 100,
        max_depth=3,
        num_leaves=7,
        reg_alpha=1.0,
        reg_lambda=5.0,
        random_state=42,
        verbose=-1,
    )
    lgb_temp.fit(X_temp_train, delta_train)
    val_pred_lgb = raw_val + lgb_temp.predict(X_temp_val)
    val_mae_lgb = float(np.mean(np.abs(val_pred_lgb - y_temp_val)))

    # Train LightGBM Quantile Regressors (p10, p90)
    print("Fitting LightGBM Quantile Regressors (p10, p90)...")
    lgb_p10 = LGBMRegressor(
        objective="quantile",
        alpha=0.10,
        n_estimators=50,
        learning_rate=3 / 100,
        max_depth=3,
        random_state=42,
        verbose=-1,
    )
    lgb_p10.fit(X_temp_train, delta_train)

    lgb_p90 = LGBMRegressor(
        objective="quantile",
        alpha=0.90,
        n_estimators=50,
        learning_rate=3 / 100,
        max_depth=3,
        random_state=42,
        verbose=-1,
    )
    lgb_p90.fit(X_temp_train, delta_train)

    # 4. Rain Occurrence Models
    X_rain_train, y_rain_train = _extract_rain_features(train_rows)
    X_rain_val, y_rain_val = _extract_rain_features(val_rows)

    print("Fitting Rain Logistic Regression...")
    lr_rain = LogisticRegression(C=0.5, max_iter=500, random_state=42)
    lr_rain.fit(X_rain_train, y_rain_train)
    val_p_lr = lr_rain.predict_proba(X_rain_val)[:, 1]
    val_brier_lr = float(np.mean((val_p_lr - y_rain_val) ** 2))

    print("Fitting Rain LightGBM Classifier...")
    lgb_rain = LGBMClassifier(
        n_estimators=50,
        learning_rate=3 / 100,
        max_depth=3,
        reg_alpha=0.5,
        reg_lambda=2.0,
        random_state=42,
        verbose=-1,
    )
    lgb_rain.fit(X_rain_train, y_rain_train)
    val_p_lgb = lgb_rain.predict_proba(X_rain_val)[:, 1]
    val_brier_lgb = float(np.mean((val_p_lgb - y_rain_val) ** 2))

    print(f"Validation MAE: Ridge={val_mae_ridge:.4f}°C, LightGBM={val_mae_lgb:.4f}°C")
    print(f"Validation Rain Brier: Logistic={val_brier_lr:.4f}, LightGBM={val_brier_lgb:.4f}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Save real model artifacts using joblib (Rule T1)
    ridge_bundle = {
        "model_type": "Ridge",
        "temp_ridge": ridge,
        "p10_offset": p10_offset,
        "p90_offset": p90_offset,
        "rain_logistic": lr_rain,
        "temp_features": TEMP_FEATURE_COLS,
        "rain_features": RAIN_FEATURE_COLS,
    }
    joblib.dump(ridge_bundle, RIDGE_MODEL_FILE)
    print(f"[OK] Saved Ridge model artifact to {RIDGE_MODEL_FILE}")

    lgbm_bundle = {
        "model_type": "LightGBM",
        "temp_lgbm": lgb_temp,
        "p10_lgbm": lgb_p10,
        "p90_lgbm": lgb_p90,
        "rain_lgbm": lgb_rain,
        "temp_features": TEMP_FEATURE_COLS,
        "rain_features": RAIN_FEATURE_COLS,
    }
    joblib.dump(lgbm_bundle, LGBM_MODEL_FILE)
    print(f"[OK] Saved LightGBM model artifact to {LGBM_MODEL_FILE}")

    artifacts_meta: dict[str, Any] = {
        "model_version": "bias_correction_v2.0",
        "training_window": f"{TRAIN_START_DATE} to {TRAIN_END_DATE}",
        "validation_window": f"{VAL_START_DATE} to {VAL_END_DATE}",
        "n_train_samples": len(train_rows),
        "n_val_samples": len(val_rows),
        "temperature_features": TEMP_FEATURE_COLS,
        "rain_features": RAIN_FEATURE_COLS,
        "models_trained": ["Ridge", "LightGBM"],
        "ridge_coefficients": [float(c) for c in ridge.coef_],
        "ridge_intercept": float(ridge.intercept_),
        "ridge_p10_offset": p10_offset,
        "ridge_p90_offset": p90_offset,
        "logistic_coefficients": [float(c) for c in lr_rain.coef_[0]],
        "logistic_intercept": float(lr_rain.intercept_[0]),
        "validation_performance": {
            "ridge_mae": val_mae_ridge,
            "lgbm_mae": val_mae_lgb,
            "logistic_rain_brier": val_brier_lr,
            "lgbm_rain_brier": val_brier_lgb,
        },
    }
    with ARTIFACTS_JSON_FILE.open("w", encoding="utf-8") as f:
        json.dump(artifacts_meta, f, indent=2)

    # Remove obsolete model_weights.json if present per Ticket R20.6
    if LEGACY_WEIGHTS_FILE.exists():
        LEGACY_WEIGHTS_FILE.unlink()
        print(f"[OK] Removed legacy unprincipled {LEGACY_WEIGHTS_FILE}")

    print(f"[OK] Training complete. Artifact metadata saved to {ARTIFACTS_JSON_FILE}")
    return artifacts_meta


def main() -> int:
    train_models()
    return 0


if __name__ == "__main__":
    main()
