"""Train point-forecast bias correction models on real observations (Ticket R11).

Trains:
- Temperature MOS Ridge Regression (minimizes MAE / RMSE)
- Quantile Regression (p10, p50, p90) via Iteratively Reweighted Least Squares (IRLS)
- Calibrated probability of precipitation (rain occurrence >= 2.5 mm)

Saves trained artifacts to ml/bias_correction/artifacts/model_weights.json.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

from ml.bias_correction.dataset import get_time_splits, load_dataset

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
ARTIFACTS_DIR = ROOT / "ml" / "bias_correction" / "artifacts"
WEIGHTS_FILE = ARTIFACTS_DIR / "model_weights.json"


def _extract_temp_features(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    """Extract design matrix X and target y for temperature models."""
    x_list = []
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

        feat = [1.0, lead, gfs, ecmwf, icon, mmm, doy_s, doy_c, lat, lon, elev, rec_bias]
        x_list.append(feat)
        y_list.append(float(r["observed_tmax"]))

    return np.array(x_list, dtype=float), np.array(y_list, dtype=float)


def _extract_rain_features(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    """Extract design matrix X and target y for rain occurrence models."""
    x_list = []
    y_list = []

    for r in rows:
        lead = float(r["lead_day"])
        rain_mmm = max(0, float(r["rain_mmm"]))
        log_rain = math.log1p(rain_mmm)
        gfs_rain = max(0, float(r["rain_gfs"]))
        ecm_rain = max(0, float(r["rain_ecmwf"]))
        d = r["date"]
        month = int(d.split("-")[1])
        is_monsoon = 1.0 if 6 <= month <= 9 else 0.0
        lat = float(r["lat"]) / 10.0

        feat = [1.0, lead, rain_mmm, log_rain, gfs_rain, ecm_rain, is_monsoon, lat]
        x_list.append(feat)
        y_list.append(int(r["observed_rain_event"]))

    return np.array(x_list, dtype=float), np.array(y_list, dtype=float)


def fit_ridge(X: np.ndarray, y: np.ndarray, l2_reg: float = 1.0) -> list[float]:
    """Solve regularized least squares: (X^T X + l2_reg * I) w = X^T y."""
    n_features = X.shape[1]
    xtx = X.T @ X
    # Do not penalize intercept (feature 0)
    reg_matrix = np.eye(n_features) * l2_reg
    reg_matrix[0, 0] = 0.0

    xty = X.T @ y
    w = np.linalg.solve(xtx + reg_matrix, xty)
    return [float(v) for v in w]


def fit_quantile_irls(
    X: np.ndarray,
    y: np.ndarray,
    tau: float,
    max_iter: int = 30,
    l2_reg: float = 0.1,
    tol: float = 1e-4,
) -> list[float]:
    """Fit linear quantile regression using Iteratively Reweighted Least Squares (IRLS).

    Loss: sum(rho_tau(y - X w)) where rho_tau(u) = u * (tau - I(u < 0)).
    """
    n, p = X.shape
    # Initialize with ridge OLS solution
    w = np.array(fit_ridge(X, y, l2_reg=1.0))

    reg_diag = np.eye(p) * l2_reg
    reg_diag[0, 0] = 0.0

    for _ in range(max_iter):
        residuals = y - X @ w
        # Asymmetric weights with smoothing parameter epsilon
        eps = 1e-3
        abs_r = np.maximum(np.abs(residuals), eps)
        weights = np.where(residuals >= 0, tau / abs_r, (1.0 - tau) / abs_r)

        # Solve (X^T W X + reg) w_new = X^T W y
        W_sqrt = np.sqrt(weights)
        X_w = X * W_sqrt[:, np.newaxis]
        y_w = y * W_sqrt

        w_new = np.linalg.solve(X_w.T @ X_w + reg_diag, X_w.T @ y_w)
        if np.max(np.abs(w_new - w)) < tol:
            break
        w = w_new

    return [float(v) for v in w]


def fit_logistic(X: np.ndarray, y: np.ndarray, max_iter: int = 50, lr: float = 0.05, l2_reg: float = 0.5) -> list[float]:
    """Fit regularized logistic regression for rain probability."""
    n, p = X.shape
    w = np.zeros(p)

    for _ in range(max_iter):
        z = np.clip(X @ w, -15.0, 15.0)
        p_hat = 1.0 / (1.0 + np.exp(-z))
        gradient = (X.T @ (p_hat - y)) / n
        gradient[1:] += (l2_reg / n) * w[1:]
        w -= lr * gradient

    return [float(v) for v in w]


def train_models() -> dict[str, Any]:
    """Load real training data and fit temperature and rain models."""
    print("ml.bias_correction.train: Loading training dataset...")
    rows = load_dataset()
    train_rows, test_rows = get_time_splits(rows)

    print(f"Dataset split: {len(train_rows)} train rows, {len(test_rows)} test rows (7-day embargo enforced).")
    if not train_rows:
        raise ValueError("Training set is empty; run 'python scripts/dev.py ml download bias_correction' first.")

    # 1. Temperature Ridge Regression
    X_temp_train, y_temp_train = _extract_temp_features(train_rows)
    print(f"Fitting Temperature Ridge Regression on {len(train_rows)} samples...")
    ridge_weights = fit_ridge(X_temp_train, y_temp_train, l2_reg=1.0)

    # 2. Quantile Regression (p10, p50, p90)
    print("Fitting Quantile Regression models (p10, p50, p90) via IRLS...")
    p10_weights = fit_quantile_irls(X_temp_train, y_temp_train, tau=0.10)
    p50_weights = fit_quantile_irls(X_temp_train, y_temp_train, tau=0.50)
    p90_weights = fit_quantile_irls(X_temp_train, y_temp_train, tau=0.90)

    # 3. Rain Occurrence Logistic Model
    X_rain_train, y_rain_train = _extract_rain_features(train_rows)
    print(f"Fitting Rain Occurrence Logistic model on {len(train_rows)} samples...")
    rain_weights = fit_logistic(X_rain_train, y_rain_train, max_iter=60, lr=0.08, l2_reg=0.2)

    # Calculate training climatology by DOY
    doy_sums: dict[int, list[float]] = {}
    for r in train_rows:
        doy_sums.setdefault(r["doy"], []).append(r["observed_tmax"])
    doy_clim = {doy: round(sum(vals) / len(vals), 2) for doy, vals in doy_sums.items()}

    artifacts: dict[str, Any] = {
        "model_version": "bias_correction_v1.0",
        "training_period": "2023-06-01 to 2024-04-23",
        "n_train_samples": len(train_rows),
        "temperature_ridge_weights": ridge_weights,
        "temperature_p10_weights": p10_weights,
        "temperature_p50_weights": p50_weights,
        "temperature_p90_weights": p90_weights,
        "rain_logistic_weights": rain_weights,
        "doy_climatology": doy_clim,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with WEIGHTS_FILE.open("w", encoding="utf-8") as f:
        json.dump(artifacts, f, indent=2)

    print(f"[OK] Training complete. Artifacts saved to {WEIGHTS_FILE}")
    return artifacts


def main() -> int:
    train_models()
    return 0


if __name__ == "__main__":
    main()
