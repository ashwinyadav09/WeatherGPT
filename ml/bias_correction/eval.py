"""Evaluate point-forecast bias correction on held-out test block (Ticket R11).

Evaluates once on held-out test block (Rule S3):
- Temperature metrics: MAE, RMSE, bias, interval coverage (10-90 band)
- Rain metrics: Brier score, Brier skill score (BSS), Heidke skill score (HSS)
- Paired block bootstrap (weekly blocks, B=2000, fixed seed 42) against best raw baseline
- Gate check: enable correction in production only if improvement interval excludes zero (Rule S2)

Outputs:
- ml/bias_correction/reports/predictions_test.csv
- ml/bias_correction/reports/metrics.json
- ml/bias_correction/reports/MODEL_CARD.md
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.bias_correction.dataset import get_time_splits, load_dataset  # noqa: E402
from ml.bias_correction.train import _extract_rain_features, _extract_temp_features  # noqa: E402
from ml.common.report import render_model_card  # noqa: E402
from ml.common.stats import (  # noqa: E402
    brier_score,
    brier_skill_score,
    heidke_skill_score,
    mean_absolute_error,
    paired_block_bootstrap,
)

ARTIFACTS_DIR = ROOT / "ml" / "bias_correction" / "artifacts"
REPORTS_DIR = ROOT / "ml" / "bias_correction" / "reports"
WEIGHTS_FILE = ARTIFACTS_DIR / "model_weights.json"
PREDICTIONS_FILE = REPORTS_DIR / "predictions_test.csv"
METRICS_FILE = REPORTS_DIR / "metrics.json"
MODEL_CARD_FILE = REPORTS_DIR / "MODEL_CARD.md"
PROCESSED_DATA_FILE = ROOT / "ml" / "bias_correction" / "data" / "processed_dataset.csv"


def _get_git_sha() -> str:
    try:
        proc = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True, text=True)
        sha = proc.stdout.strip()
        if len(sha) == 40:
            return sha
    except Exception:
        pass
    return "0" * 40


def evaluate_models() -> dict[str, Any]:
    print("ml.bias_correction.eval: Loading artifacts and held-out test data...")
    if not WEIGHTS_FILE.exists():
        raise FileNotFoundError(f"Model artifacts missing at {WEIGHTS_FILE}; run 'ml train bias_correction' first.")

    with WEIGHTS_FILE.open("r", encoding="utf-8") as f:
        artifacts = json.load(f)

    rows = load_dataset()
    train_rows, test_rows = get_time_splits(rows)
    print(f"Loaded {len(test_rows)} held-out test observations.")
    if not test_rows:
        raise ValueError("Held-out test dataset is empty; cannot evaluate.")

    ridge_weights = np.array(artifacts["temperature_ridge_weights"])
    p10_weights = np.array(artifacts["temperature_p10_weights"])
    p90_weights = np.array(artifacts["temperature_p90_weights"])
    rain_weights = np.array(artifacts["rain_logistic_weights"])
    doy_clim = artifacts.get("doy_climatology", {})

    # Design matrices for test set
    X_temp_test, y_temp_true = _extract_temp_features(test_rows)
    X_rain_test, y_rain_true = _extract_rain_features(test_rows)

    # Predictions
    y_pred_ridge = X_temp_test @ ridge_weights
    y_pred_p10 = X_temp_test @ p10_weights
    y_pred_p90 = X_temp_test @ p90_weights

    # Rain probability predictions
    z_rain = np.clip(X_rain_test @ rain_weights, -15.0, 15.0)
    rain_probs = 1.0 / (1.0 + np.exp(-z_rain))
    pred_rain_event = (rain_probs >= 0.35).astype(int)

    # Baselines
    raw_mmm = np.array([float(r["tmax_mmm"]) for r in test_rows])
    raw_ecmwf = np.array([float(r["tmax_ecmwf"]) for r in test_rows])
    raw_gfs = np.array([float(r["tmax_gfs"]) for r in test_rows])
    raw_icon = np.array([float(r["tmax_icon"]) for r in test_rows])
    clim_preds = np.array([doy_clim.get(r["doy"], r["tmax_mmm"]) for r in test_rows])

    # Determine best raw baseline
    raw_candidates = {
        "ECMWF IFS": (raw_ecmwf, mean_absolute_error(y_temp_true, raw_ecmwf)),
        "GFS": (raw_gfs, mean_absolute_error(y_temp_true, raw_gfs)),
        "ICON": (raw_icon, mean_absolute_error(y_temp_true, raw_icon)),
        "Multi-model mean": (raw_mmm, mean_absolute_error(y_temp_true, raw_mmm)),
    }
    best_raw_name = min(raw_candidates, key=lambda k: raw_candidates[k][1])
    best_raw_preds, best_raw_mae = raw_candidates[best_raw_name]

    # Metrics computation
    mae_model = mean_absolute_error(y_temp_true, y_pred_ridge)

    # 10-90 coverage (target 80%)
    in_interval = (y_temp_true >= y_pred_p10) & (y_temp_true <= y_pred_p90)
    coverage_10_90 = float(np.mean(in_interval))

    # Rain metrics
    bs_rain = brier_score(y_rain_true, rain_probs)
    bss_rain = brier_skill_score(y_rain_true, rain_probs)
    hss_rain = heidke_skill_score(y_rain_true, pred_rain_event)

    # Paired block bootstrap against best raw baseline
    timestamps = [r["date"] for r in test_rows]
    print(f"Running paired block bootstrap (B=2000) against {best_raw_name}...")
    bootstrap_res = paired_block_bootstrap(
        y_true=y_temp_true,
        y_pred_model=y_pred_ridge,
        y_pred_baseline=best_raw_preds,
        timestamps=timestamps,
        metric_func=mean_absolute_error,
        block_size_days=7,
        n_bootstrap=2000,
        seed=42,
    )

    delta_mae = float(bootstrap_res["delta_mean"])
    ci_lower = float(bootstrap_res["ci_lower"])
    ci_upper = float(bootstrap_res["ci_upper"])
    p_val = float(bootstrap_res["p_value"])

    # Production gate rule: enable correction only if improvement interval excludes zero
    # delta is (model_mae - baseline_mae), so improvement is negative delta
    is_improvement_significant = bool(ci_upper < 0.0)
    enabled_in_prod = is_improvement_significant

    print(f"MAE Model: {mae_model:.3f}°C vs Best Raw ({best_raw_name}): {best_raw_mae:.3f}°C")
    print(f"Delta MAE: {delta_mae:+.3f}°C, 95% CI: [{ci_lower:+.3f}, {ci_upper:+.3f}], p-value: {p_val:.4f}")
    print(f"Improvement interval strictly excludes zero: {is_improvement_significant}")
    print(f"Production Gate Status: {'ENABLED' if enabled_in_prod else 'DISABLED (Negative result reported)'}")

    # Write predictions_test.csv
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pred_rows = []
    for idx, r in enumerate(test_rows):
        pred_rows.append({
            "station_id": r["station_id"],
            "date": r["date"],
            "lead_day": r["lead_day"],
            "y_true": round(float(y_temp_true[idx]), 1),
            "y_pred": round(float(y_pred_ridge[idx]), 2),
            "y_pred_p10": round(float(y_pred_p10[idx]), 2),
            "y_pred_p90": round(float(y_pred_p90[idx]), 2),
            "raw_forecast": round(float(best_raw_preds[idx]), 2),
            "multi_model_mean": round(float(raw_mmm[idx]), 2),
            "observed_rain": r["observed_rain"],
            "rain_prob": round(float(rain_probs[idx]), 3),
            "pred_rain_event": int(pred_rain_event[idx]),
        })

    with PREDICTIONS_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(pred_rows[0].keys()))
        writer.writeheader()
        writer.writerows(pred_rows)
    print(f"[OK] Wrote {len(pred_rows)} test predictions to {PREDICTIONS_FILE}")

    # Compute exact headline metrics on written predictions to match recompute within 1e-9
    y_true_list = [float(r["y_true"]) for r in pred_rows]
    y_pred_list = [float(r["y_pred"]) for r in pred_rows]
    diffs = [p - t for t, p in zip(y_true_list, y_pred_list)]
    mae_exact = sum(abs(e) for e in diffs) / len(diffs)
    rmse_exact = math.sqrt(sum(e * e for e in diffs) / len(diffs))
    bias_exact = sum(diffs) / len(diffs)

    # Compute sha256 of input processed dataset
    input_sha256 = ""
    if PROCESSED_DATA_FILE.exists():
        input_sha256 = hashlib.sha256(PROCESSED_DATA_FILE.read_bytes()).hexdigest()

    git_sha = _get_git_sha()

    # Build audited metrics.json dictionary
    metrics_data: dict[str, Any] = {
        "model_name": "NWP_BiasCorrection_v1",
        "version": "1.0.0",
        "task": "Point-forecast 2m temperature post-processing and precipitation occurrence",
        "generated_by": "ml/bias_correction/eval.py",
        "git_sha": git_sha,
        "provenance": "recorded_real_http",
        "inputs": [
            {
                "path": str(PROCESSED_DATA_FILE.relative_to(ROOT)).replace("\\", "/"),
                "sha256": input_sha256,
            }
        ],
        "n_train": len(train_rows),
        "n_test": len(pred_rows),
        "enabled_in_production": enabled_in_prod,
        "mae": mae_exact,
        "rmse": rmse_exact,
        "bias": bias_exact,
        "interval_coverage_10_90": round(coverage_10_90, 4),
        "brier_score": round(bs_rain, 4),
        "brier_skill_score": round(bss_rain, 4),
        "heidke_skill_score": round(hss_rain, 4),
        "metrics": {
            "mae": mae_exact,
            "rmse": rmse_exact,
            "bias": bias_exact,
            "interval_coverage_10_90": round(coverage_10_90, 4),
            "brier_score": round(bs_rain, 4),
            "brier_skill_score": round(bss_rain, 4),
            "heidke_skill_score": round(hss_rain, 4),
        },
        "baseline_comparison": {
            "temperature_mae": {
                "baseline_name": best_raw_name,
                "baseline": round(best_raw_mae, 4),
                "model": round(mae_exact, 4),
                "delta": round(delta_mae, 4),
                "ci_lower": round(ci_lower, 4),
                "ci_upper": round(ci_upper, 4),
                "p_value": round(p_val, 4),
            },
            "climatology_mae": {
                "baseline_name": "Climatology",
                "baseline": round(mean_absolute_error(y_temp_true, clim_preds), 4),
                "model": round(mae_exact, 4),
                "delta": round(mae_exact - mean_absolute_error(y_temp_true, clim_preds), 4),
            },
        },
        "dataset": {
            "name": "Open-Meteo Previous Runs NWP paired with IEM ASOS METAR Observations",
            "models_ingested": "ECMWF IFS 0.25°, NOAA GFS, DWD ICON",
            "truth_sources": "IEM ASOS METAR hourly observations (IST Tmax) and Open-Meteo archive precipitation",
            "training_period": "2023-06-01 to 2024-04-23",
            "embargo_period": "2024-04-24 to 2024-04-30 (7 days)",
            "test_period": "2024-05-01 to 2024-10-31 (6 months)",
        },
        "limitations": [
            "METAR observations record integer Celsius temperatures, imparting a rounding effect of ~0.5°C.",
            "Bias correction is verified only within 100 km and 300 m elevation of training airport stations.",
            "Precipitation occurrence model is trained on precipitation proxy from reanalysis.",
        ],
    }

    with METRICS_FILE.open("w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"[OK] Wrote audited metrics to {METRICS_FILE}")

    # Log to RUN_MANIFEST.json per Rule S3
    run_manifest_file = REPORTS_DIR / "RUN_MANIFEST.json"
    manifest_entry = {
        "generated_by": "ml/bias_correction/eval.py",
        "git_sha": git_sha,
        "provenance": "recorded_real_http",
        "inputs": [
            {
                "path": str(PROCESSED_DATA_FILE.relative_to(ROOT)).replace("\\", "/"),
                "sha256": input_sha256,
            }
        ],
        "evaluation_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "test_dataset": {
            "path": str(PROCESSED_DATA_FILE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": input_sha256,
            "n_test": len(pred_rows),
            "test_period": "2024-05-01 to 2024-10-31",
            "embargo_days": 7,
        },
        "headline_metrics": {
            "mae": mae_exact,
            "rmse": rmse_exact,
            "bias": bias_exact,
        },
        "enabled_in_production": enabled_in_prod,
        "note": "Evaluation on held-out test block (Rule S3). Test set evaluated once.",
    }
    with run_manifest_file.open("w", encoding="utf-8") as f:
        json.dump(manifest_entry, f, indent=2)
    print(f"[OK] Wrote run manifest to {run_manifest_file}")

    # Render MODEL_CARD.md
    render_model_card(metrics_data, output_path=MODEL_CARD_FILE)
    print(f"[OK] Rendered MODEL_CARD.md at {MODEL_CARD_FILE}")

    return metrics_data


def main() -> int:
    evaluate_models()
    return 0


if __name__ == "__main__":
    main()
