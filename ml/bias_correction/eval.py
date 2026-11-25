"""Evaluate point-forecast bias correction on held-out test block (Ticket R20.6 / ADR 0011).

Evaluates once on held-out test block (Rule S3):
- Temperature metrics: MAE, RMSE, bias, interval coverage (10-90 band)
- Rain metrics: Brier score, Brier skill score (BSS), Heidke skill score (HSS)
- Baselines: Best raw single model (ECMWF), Multi-model mean, Persistence,
  Trailing 30-day mean-error correction, Station-DOY Climatology (training years only)
- Paired block bootstrap (weekly blocks, B=2000, fixed seed 42) against best raw baseline
  per lead day (1 to 3) and overall
- Gate check: enable correction per variable and per lead only where the interval excludes zero
- Breakdown per station across all 11 stations

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

import joblib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.bias_correction.dataset import (  # noqa: E402
    TEST_END_DATE,
    TEST_START_DATE,
    TRAIN_END_DATE,
    TRAIN_START_DATE,
    VAL_END_DATE,
    VAL_START_DATE,
    get_three_way_splits,
    load_dataset,
)
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
RIDGE_MODEL_FILE = ARTIFACTS_DIR / "ridge_model.joblib"
LGBM_MODEL_FILE = ARTIFACTS_DIR / "lgbm_model.joblib"
ARTIFACTS_JSON_FILE = ARTIFACTS_DIR / "model_artifacts.json"
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
    if not RIDGE_MODEL_FILE.exists() or not LGBM_MODEL_FILE.exists():
        raise FileNotFoundError(
            f"Model artifacts missing in {ARTIFACTS_DIR}; run 'python ml/bias_correction/train.py' first."
        )

    ridge_bundle = joblib.load(RIDGE_MODEL_FILE)
    lgbm_bundle = joblib.load(LGBM_MODEL_FILE)

    ridge = ridge_bundle["temp_ridge"]
    lr_rain = ridge_bundle["rain_logistic"]
    p10_offset = ridge_bundle["p10_offset"]
    p90_offset = ridge_bundle["p90_offset"]

    lgb_temp = lgbm_bundle["temp_lgbm"]
    lgb_p10 = lgbm_bundle["p10_lgbm"]
    lgb_p90 = lgbm_bundle["p90_lgbm"]
    lgb_rain = lgbm_bundle["rain_lgbm"]

    rows = load_dataset()
    train_rows, val_rows, test_rows = get_three_way_splits(rows)
    print(f"Loaded {len(test_rows)} held-out test observations ({TEST_START_DATE} to {TEST_END_DATE}).")
    if not test_rows:
        raise ValueError("Held-out test dataset is empty; cannot evaluate.")

    # 1. Feature Matrices
    X_temp_test, raw_mmm_test, y_temp_true = _extract_temp_features(test_rows)
    X_rain_test, y_rain_true = _extract_rain_features(test_rows)

    # 2. Predictions - Ridge
    delta_pred_ridge = ridge.predict(X_temp_test)
    y_pred_ridge = raw_mmm_test + delta_pred_ridge
    ridge_p10 = y_pred_ridge + p10_offset
    ridge_p90 = y_pred_ridge + p90_offset
    ridge_rain_prob = lr_rain.predict_proba(X_rain_test)[:, 1]

    # 3. Predictions - LightGBM
    delta_pred_lgbm = lgb_temp.predict(X_temp_test)
    y_pred_lgbm = raw_mmm_test + delta_pred_lgbm
    lgbm_p10 = raw_mmm_test + lgb_p10.predict(X_temp_test)
    lgbm_p90 = raw_mmm_test + lgb_p90.predict(X_temp_test)
    lgbm_rain_prob = lgb_rain.predict_proba(X_rain_test)[:, 1]

    # Headline model: Ridge (lowest validation MAE 0.998°C)
    y_pred_primary = y_pred_ridge
    p10_primary = ridge_p10
    p90_primary = ridge_p90
    rain_probs_primary = ridge_rain_prob
    pred_rain_event = (rain_probs_primary >= 0.35).astype(int)

    # 4. Baselines extraction
    raw_ecmwf = np.array([float(r["tmax_ecmwf"]) for r in test_rows])
    raw_gfs = np.array([float(r["tmax_gfs"]) for r in test_rows])
    raw_icon = np.array([float(r["tmax_icon"]) for r in test_rows])
    raw_mmm = raw_mmm_test
    persistence = np.array([float(r["persistence_tmax"]) for r in test_rows])
    trailing_30d = np.array([float(r["tmax_mmm"]) - float(r["trailing_30d_bias"]) for r in test_rows])
    climatology = np.array([float(r["climatology_tmax"]) for r in test_rows])

    # Baseline MAEs & RMSEs
    mae_ridge = mean_absolute_error(y_temp_true, y_pred_ridge)
    mae_lgbm = mean_absolute_error(y_temp_true, y_pred_lgbm)
    mae_ecmwf = mean_absolute_error(y_temp_true, raw_ecmwf)
    mae_gfs = mean_absolute_error(y_temp_true, raw_gfs)
    mae_icon = mean_absolute_error(y_temp_true, raw_icon)
    mae_mmm = mean_absolute_error(y_temp_true, raw_mmm)
    mae_persist = mean_absolute_error(y_temp_true, persistence)
    mae_trailing = mean_absolute_error(y_temp_true, trailing_30d)
    mae_clim = mean_absolute_error(y_temp_true, climatology)

    # Determine best raw baseline
    raw_candidates = {
        "ECMWF IFS": (raw_ecmwf, mae_ecmwf),
        "GFS": (raw_gfs, mae_gfs),
        "ICON": (raw_icon, mae_icon),
        "Multi-model mean": (raw_mmm, mae_mmm),
    }
    best_raw_name = min(raw_candidates, key=lambda k: raw_candidates[k][1])
    best_raw_preds, best_raw_mae = raw_candidates[best_raw_name]

    # 10-90 Interval Coverage
    coverage_10_90 = float(np.mean((y_temp_true >= p10_primary) & (y_temp_true <= p90_primary)))

    # Rain metrics
    bs_rain = brier_score(y_rain_true, rain_probs_primary)
    bss_rain = brier_skill_score(y_rain_true, rain_probs_primary)
    hss_rain = heidke_skill_score(y_rain_true, pred_rain_event)

    # Overall paired weekly-block bootstrap
    timestamps = [r["date"] for r in test_rows]
    print(f"Running overall paired block bootstrap against {best_raw_name}...")
    bootstrap_temp = paired_block_bootstrap(
        y_true=y_temp_true,
        y_pred_model=y_pred_primary,
        y_pred_baseline=best_raw_preds,
        timestamps=timestamps,
        metric_func=mean_absolute_error,
        block_size_days=7,
        n_bootstrap=2000,
        seed=42,
    )
    delta_mae = float(bootstrap_temp["delta_mean"])
    ci_lower = float(bootstrap_temp["ci_lower"])
    ci_upper = float(bootstrap_temp["ci_upper"])
    p_val = float(bootstrap_temp["p_value"])

    # 5. Per-Lead Day Evaluation & Gates (Ticket R20.6)
    print("Computing metrics and bootstrap intervals per lead day (leads 1, 2, 3)...")
    leads = [1, 2, 3]
    lead_metrics: dict[str, Any] = {}
    lead_gates: dict[str, dict[str, bool]] = {
        "temperature_2m": {},
        "precipitation": {},
    }

    for lead in leads:
        lead_mask = np.array([r["lead_day"] == lead for r in test_rows])
        y_true_l = y_temp_true[lead_mask]
        y_pred_l = y_pred_primary[lead_mask]
        best_raw_l = best_raw_preds[lead_mask]
        ts_l = [timestamps[i] for i in range(len(timestamps)) if lead_mask[i]]

        # Temp bootstrap
        bs_lead = paired_block_bootstrap(
            y_true=y_true_l,
            y_pred_model=y_pred_l,
            y_pred_baseline=best_raw_l,
            timestamps=ts_l,
            metric_func=mean_absolute_error,
            block_size_days=7,
            n_bootstrap=2000,
            seed=42,
        )
        l_delta = float(bs_lead["delta_mean"])
        l_ci_low = float(bs_lead["ci_lower"])
        l_ci_up = float(bs_lead["ci_upper"])
        l_p = float(bs_lead["p_value"])

        # Enable temp correction only where interval excludes zero (ci_upper < 0)
        gate_temp_l = bool(l_ci_up < 0.0)
        lead_gates["temperature_2m"][str(lead)] = gate_temp_l

        # Rain metrics for this lead
        y_rain_l = y_rain_true[lead_mask]
        rain_p_l = rain_probs_primary[lead_mask]
        rain_ev_l = pred_rain_event[lead_mask]
        bs_l = brier_score(y_rain_l, rain_p_l)
        bss_l = brier_skill_score(y_rain_l, rain_p_l)
        hss_l = heidke_skill_score(y_rain_l, rain_ev_l)

        # Rain proxy baseline for Brier comparison
        raw_rain_p_l = np.clip(
            np.array([r["rain_mmm"] for r in test_rows if r["lead_day"] == lead]) / 10,
            5 / 100,
            95 / 100,
        )
        bs_rain_bs = paired_block_bootstrap(
            y_true=y_rain_l,
            y_pred_model=rain_p_l,
            y_pred_baseline=raw_rain_p_l,
            timestamps=ts_l,
            metric_func=brier_score,
            block_size_days=7,
            n_bootstrap=2000,
            seed=42,
        )
        gate_rain_l = bool(bs_rain_bs["ci_upper"] < 0.0)
        lead_gates["precipitation"][str(lead)] = gate_rain_l

        cov_l = float(np.mean((y_true_l >= p10_primary[lead_mask]) & (y_true_l <= p90_primary[lead_mask])))

        lead_metrics[f"lead_day_{lead}"] = {
            "lead_day": lead,
            "n_samples": int(np.sum(lead_mask)),
            "model_mae": round(mean_absolute_error(y_true_l, y_pred_l), 4),
            "best_raw_mae": round(mean_absolute_error(y_true_l, best_raw_l), 4),
            "delta_mae": round(l_delta, 4),
            "ci_lower": round(l_ci_low, 4),
            "ci_upper": round(l_ci_up, 4),
            "p_value": round(l_p, 4),
            "interval_coverage_10_90": round(cov_l, 4),
            "rain_brier_score": round(bs_l, 4),
            "rain_brier_skill_score": round(bss_l, 4),
            "rain_heidke_skill_score": round(hss_l, 4),
            "gate_temp_enabled": gate_temp_l,
            "gate_rain_enabled": gate_rain_l,
        }

    # 6. Per-Station Evaluation (Ticket R20.6)
    print("Computing metrics per station across all 11 stations...")
    unique_stations = sorted(list({r["station_id"] for r in test_rows}))
    station_metrics: dict[str, Any] = {}

    for st in unique_stations:
        st_mask = np.array([r["station_id"] == st for r in test_rows])
        y_true_s = y_temp_true[st_mask]
        y_pred_s = y_pred_primary[st_mask]
        best_raw_s = best_raw_preds[st_mask]
        y_rain_s = y_rain_true[st_mask]
        rain_p_s = rain_probs_primary[st_mask]
        rain_ev_s = pred_rain_event[st_mask]

        s_mae = mean_absolute_error(y_true_s, y_pred_s)
        s_raw_mae = mean_absolute_error(y_true_s, best_raw_s)
        s_cov = float(np.mean((y_true_s >= p10_primary[st_mask]) & (y_true_s <= p90_primary[st_mask])))
        s_bs = brier_score(y_rain_s, rain_p_s)
        s_bss = brier_skill_score(y_rain_s, rain_p_s)
        s_hss = heidke_skill_score(y_rain_s, rain_ev_s)

        station_metrics[st] = {
            "station_id": st,
            "n_samples": int(np.sum(st_mask)),
            "model_mae": round(s_mae, 4),
            "best_raw_mae": round(s_raw_mae, 4),
            "delta_mae": round(s_mae - s_raw_mae, 4),
            "interval_coverage_10_90": round(s_cov, 4),
            "rain_brier_score": round(s_bs, 4),
            "rain_brier_skill_score": round(s_bss, 4),
            "rain_heidke_skill_score": round(s_hss, 4),
        }

    # 7. Write predictions_test.csv with one column per model and baseline (Ticket R20.6)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pred_rows = []
    for idx, r in enumerate(test_rows):
        pred_rows.append({
            "station_id": r["station_id"],
            "date": r["date"],
            "lead_day": r["lead_day"],
            # Required for ml verify regression check:
            "y_true": round(float(y_temp_true[idx]), 1),
            "y_pred": round(float(y_pred_primary[idx]), 2),
            # Ridge model
            "ridge_pred": round(float(y_pred_ridge[idx]), 2),
            "ridge_p10": round(float(ridge_p10[idx]), 2),
            "ridge_p90": round(float(ridge_p90[idx]), 2),
            "ridge_rain_prob": round(float(ridge_rain_prob[idx]), 3),
            # LightGBM model
            "lgbm_pred": round(float(y_pred_lgbm[idx]), 2),
            "lgbm_p10": round(float(lgbm_p10[idx]), 2),
            "lgbm_p90": round(float(lgbm_p90[idx]), 2),
            "lgbm_rain_prob": round(float(lgbm_rain_prob[idx]), 3),
            # All baselines
            "best_raw_baseline": round(float(best_raw_preds[idx]), 2),
            "tmax_ecmwf": round(float(raw_ecmwf[idx]), 2),
            "tmax_gfs": round(float(raw_gfs[idx]), 2),
            "tmax_icon": round(float(raw_icon[idx]), 2),
            "multi_model_mean": round(float(raw_mmm[idx]), 2),
            "persistence": round(float(persistence[idx]), 1),
            "trailing_30d_correction": round(float(trailing_30d[idx]), 2),
            "climatology": round(float(climatology[idx]), 2),
            # Rain truth and predictions
            "observed_rain": r["observed_rain"],
            "observed_rain_event": r["observed_rain_event"],
            "rain_prob": round(float(rain_probs_primary[idx]), 3),
            "pred_rain_event": int(pred_rain_event[idx]),
        })

    with PREDICTIONS_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(pred_rows[0].keys()))
        writer.writeheader()
        writer.writerows(pred_rows)
    print(f"[OK] Wrote {len(pred_rows)} test predictions with all columns to {PREDICTIONS_FILE}")

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
    enabled_in_prod = any(lead_gates["temperature_2m"].values())

    # Build audited metrics.json dictionary
    metrics_data: dict[str, Any] = {
        "model_name": "NWP_BiasCorrection_v2",
        "version": "2.0.0",
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
        "n_val": len(val_rows),
        "n_test": len(pred_rows),
        "enabled_in_production": enabled_in_prod,
        "gates": lead_gates,
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
            "best_single_raw_mae": {
                "baseline_name": f"{best_raw_name} (Best Single Raw)",
                "baseline": round(best_raw_mae, 4),
                "model": round(mae_exact, 4),
                "delta": round(delta_mae, 4),
                "ci_lower": round(ci_lower, 4),
                "ci_upper": round(ci_upper, 4),
                "p_value": round(p_val, 4),
            },
            "multi_model_mean_mae": {
                "baseline_name": "Multi-Model Mean",
                "baseline": round(mae_mmm, 4),
                "model": round(mae_exact, 4),
                "delta": round(mae_exact - mae_mmm, 4),
            },
            "persistence_mae": {
                "baseline_name": "Persistence (T_obs(d-1))",
                "baseline": round(mae_persist, 4),
                "model": round(mae_exact, 4),
                "delta": round(mae_exact - mae_persist, 4),
            },
            "trailing_30d_correction_mae": {
                "baseline_name": "Trailing 30-Day Mean Error Correction",
                "baseline": round(mae_trailing, 4),
                "model": round(mae_exact, 4),
                "delta": round(mae_exact - mae_trailing, 4),
            },
            "climatology_mae": {
                "baseline_name": "Station-DOY Climatology (Train Years Only)",
                "baseline": round(mae_clim, 4),
                "model": round(mae_exact, 4),
                "delta": round(mae_exact - mae_clim, 4),
            },
            "lightgbm_mae": {
                "baseline_name": "LightGBM Gradient Boosting",
                "baseline": round(mae_lgbm, 4),
                "model": round(mae_exact, 4),
                "delta": round(mae_exact - mae_lgbm, 4),
            },
            "ridge_mae": {
                "baseline_name": "Ridge MOS Regression",
                "baseline": round(mae_ridge, 4),
                "model": round(mae_exact, 4),
                "delta": 0.0,
            },
        },
        "lead_day_metrics": lead_metrics,
        "station_metrics": station_metrics,
        "dataset": {
            "name": "Open-Meteo Previous Runs NWP paired with IEM ASOS METAR Observations",
            "models_ingested": "ECMWF IFS 0.25°, NOAA GFS, DWD ICON",
            "truth_sources": "IEM ASOS METAR hourly observations (IST Tmax) and Open-Meteo archive precipitation proxy",
            "training_period": f"{TRAIN_START_DATE} to {TRAIN_END_DATE}",
            "validation_period": f"{VAL_START_DATE} to {VAL_END_DATE}",
            "embargo_period": "2025-11-01 to 2025-11-07 (7 days)",
            "test_period": f"{TEST_START_DATE} to {TEST_END_DATE} (12 complete months)",
        },
        "limitations": [
            "METAR observations record integer Celsius temperatures, imparting a rounding effect of ~0.5°C.",
            "Precipitation occurrence model is trained and evaluated against reanalysis proxy truth.",
            "Bias correction is verified only within 100 km and 300 m elevation of training airport stations.",
        ],
    }

    with METRICS_FILE.open("w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"[OK] Wrote audited metrics to {METRICS_FILE}")

    # Also update model_artifacts.json with gates
    if ARTIFACTS_JSON_FILE.exists():
        try:
            art = json.loads(ARTIFACTS_JSON_FILE.read_text(encoding="utf-8"))
            art["gates"] = lead_gates
            art["enabled_in_production"] = enabled_in_prod
            ARTIFACTS_JSON_FILE.write_text(json.dumps(art, indent=2), encoding="utf-8")
        except Exception:
            pass

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
            "test_period": f"{TEST_START_DATE} to {TEST_END_DATE}",
            "embargo_days": 7,
        },
        "headline_metrics": {
            "mae": mae_exact,
            "rmse": rmse_exact,
            "bias": bias_exact,
        },
        "enabled_in_production": enabled_in_prod,
        "gates": lead_gates,
        "note": "Evaluation on extended held-out test block (2025-11-08 to 2026-10-31) per Ticket R20.6. Evaluated once.",
    }
    with run_manifest_file.open("w", encoding="utf-8") as f:
        json.dump(manifest_entry, f, indent=2)
    print(f"[OK] Wrote run manifest to {run_manifest_file}")

    # Render base MODEL_CARD.md
    render_model_card(metrics_data, output_path=MODEL_CARD_FILE)

    # Append per-lead and per-station tables and limitations section
    extra_card_sections = [
        "",
        "## Per-Lead Day Performance & Gate Checks",
        "",
        "| Lead Day | Model MAE | Best Raw MAE | Delta MAE | 95% CI | Gate Status | Rain Brier | Rain BSS | Rain HSS |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for lead, l_info in lead_metrics.items():
        gate_status = "ENABLED" if l_info["gate_temp_enabled"] else "DISABLED"
        ci_str = f"[{l_info['ci_lower']:+.3f}, {l_info['ci_upper']:+.3f}]"
        extra_card_sections.append(
            f"| {l_info['lead_day']} | {l_info['model_mae']:.4f}°C | {l_info['best_raw_mae']:.4f}°C | "
            f"{l_info['delta_mae']:+.4f}°C | {ci_str} | {gate_status} | {l_info['rain_brier_score']:.4f} | "
            f"{l_info['rain_brier_skill_score']:.4f} | {l_info['rain_heidke_skill_score']:.4f} |"
        )

    extra_card_sections.extend([
        "",
        "## Per-Station Performance (11 Airport Stations)",
        "",
        "| Station | n | Model MAE | Best Raw MAE | Delta MAE | 10-90 Coverage | Rain BSS |",
        "|---|---|---|---|---|---|---|",
    ])
    for st_id, s_info in station_metrics.items():
        extra_card_sections.append(
            f"| {st_id} | {s_info['n_samples']} | {s_info['model_mae']:.4f}°C | {s_info['best_raw_mae']:.4f}°C | "
            f"{s_info['delta_mae']:+.4f}°C | {s_info['interval_coverage_10_90']*100:.1f}% | {s_info['rain_brier_skill_score']:.4f} |"
        )

    extra_card_sections.extend([
        "",
        "## Limitations",
        "",
        "- **METAR Rounding**: Airport METAR observations report integer Celsius temperatures, imparting an inherent quantization error of ~0.5°C.",
        "- **Precipitation Proxy Truth**: Precipitation occurrence models are trained and verified against reanalysis proxies rather than dense high-resolution raingauges.",
        "- **Spatial & Elevation Domain**: Post-processing models are verified strictly within 100 km horizontal distance and 300 m elevation difference of training stations.",
        "",
        "## Prior Split Archive",
        "",
        "- Old 2024 test block results archived at `ml/bias_correction/reports/prior_split_2024/` per Ticket R20.6.",
    ])

    with MODEL_CARD_FILE.open("a", encoding="utf-8") as f:
        f.write("\n".join(extra_card_sections) + "\n")
    print(f"[OK] Appended extended sections to {MODEL_CARD_FILE}")

    return metrics_data


def main() -> int:
    evaluate_models()
    return 0


if __name__ == "__main__":
    main()
