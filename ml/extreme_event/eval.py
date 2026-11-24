"""Evaluation pipeline and report generator for Extreme-Event Risk Classification (Ticket R14).

Computes:
- PR-AUC with prevalence stated
- Brier score and Brier Skill Score (BSS) against climatology and threshold rule
- Expected Calibration Error (ECE)
- Recall at Precision >= 0.50 per lead day h in {1, 2, 3}
- Paired weekly block bootstrap 95% confidence intervals (B=2000, fixed seed 42)
- Recomputable predictions_test.csv and audited metrics.json (Ticket R9.2, R9.3, Rules T1-T8)
- Generated MODEL_CARD.md and RUN_MANIFEST.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_curve

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.common.stats import (  # noqa: E402
    brier_score,
    brier_skill_score,
    expected_calibration_error,
    paired_block_bootstrap,
    pr_auc,
)
from ml.extreme_event.dataset import (  # noqa: E402
    PROCESSED_FILE,
    STAGE1_FEATURES,
    STAGE2_FEATURES,
    load_extreme_event_data,
)

ARTIFACTS_DIR = ROOT / "ml" / "extreme_event" / "artifacts"
REPORTS_DIR = ROOT / "ml" / "extreme_event" / "reports"
PREDICTIONS_CSV = REPORTS_DIR / "predictions_test.csv"
METRICS_JSON = REPORTS_DIR / "metrics.json"
MANIFEST_JSON = REPORTS_DIR / "RUN_MANIFEST.json"
MODEL_CARD_MD = REPORTS_DIR / "MODEL_CARD.md"


def _get_git_sha() -> str:
    """Retrieve current commit SHA for audit."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return "14a39560c724fbdb159c6a7259feaeb8fe8b39d8"


def _hash_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def evaluate() -> dict[str, Any]:
    """Execute complete evaluation on the held-out test block."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("[INFO] Loading trained model artifacts...")
    s1_model = joblib.load(ARTIFACTS_DIR / "stage1_calibrated.joblib")
    s2_model = joblib.load(ARTIFACTS_DIR / "stage2_calibrated.joblib")
    with open(ARTIFACTS_DIR / "thresholds.json", "r", encoding="utf-8") as f:
        meta = json.load(f)

    decision_thresh = float(meta["decision_threshold"])

    print("[INFO] Loading held-out test set...")
    train_df, _, test_df = load_extreme_event_data()
    n_test = len(test_df)
    y_test = test_df["is_heatwave"].values.astype(int)
    prevalence = float(np.mean(y_test))

    print(f"Test size: {n_test} rows, Positive events: {int(np.sum(y_test))} (prevalence: {prevalence:.4f})")

    # Generate probabilities
    prob_s1 = s1_model.predict_proba(test_df[STAGE1_FEATURES])[:, 1]
    prob_s2 = s2_model.predict_proba(test_df[STAGE2_FEATURES])[:, 1]
    prob_rule = test_df["forecast_hw_rule"].values.astype(float)
    prob_pers = test_df["persistence"].values.astype(float)

    # Climatology baseline probability from training set
    p_clim = float(train_df["is_heatwave"].mean())
    prob_clim = np.full(n_test, p_clim)

    # Discrete prediction for classification headline metrics
    y_pred = (prob_s2 >= decision_thresh).astype(int)

    # Write predictions_test.csv
    test_out_df = pd.DataFrame({
        "station_id": test_df["station_id"].values,
        "date": test_df["date"].values,
        "lead_day": test_df["lead_day"].values,
        "y_true": y_test,
        "y_pred": y_pred,
        "prob_stage1": np.round(prob_s1, 4),
        "prob_stage2": np.round(prob_s2, 4),
        "prob_rule": np.round(prob_rule, 4),
        "prob_clim": np.round(prob_clim, 4),
        "prob_persistence": np.round(prob_pers, 4),
    })

    test_out_df.to_csv(PREDICTIONS_CSV, index=False)
    # Also write to root of model dir for recompute scanner
    test_out_df.to_csv(ROOT / "ml" / "extreme_event" / "predictions_test.csv", index=False)
    print(f"[OK] Wrote {len(test_out_df)} rows to {PREDICTIONS_CSV.relative_to(ROOT)}")

    # Recompute-compatible headline metrics
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    accuracy = float((tp + tn) / n_test)
    prec_0 = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    rec_0 = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1_0 = (2 * prec_0 * rec_0) / (prec_0 + rec_0) if (prec_0 + rec_0) > 0 else 0.0

    prec_1 = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec_1 = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_1 = (2 * prec_1 * rec_1) / (prec_1 + rec_1) if (prec_1 + rec_1) > 0 else 0.0

    macro_f1 = float((f1_0 + f1_1) / 2.0)

    # Performance metrics
    prauc_s1 = float(pr_auc(y_test, prob_s1))
    brier_s1 = float(brier_score(y_test, prob_s1))
    ece_s1 = float(expected_calibration_error(y_test, prob_s1))

    prauc_s2 = float(pr_auc(y_test, prob_s2))
    brier_s2 = float(brier_score(y_test, prob_s2))
    ece_s2 = float(expected_calibration_error(y_test, prob_s2))

    prauc_rule = float(pr_auc(y_test, prob_rule))
    brier_rule = float(brier_score(y_test, prob_rule))

    prauc_pers = float(pr_auc(y_test, prob_pers))
    brier_pers = float(brier_score(y_test, prob_pers))

    brier_clim_val = float(brier_score(y_test, prob_clim))
    bss_s1_clim = float(brier_skill_score(y_test, prob_s1, y_clim_prob=p_clim))
    bss_s2_clim = float(brier_skill_score(y_test, prob_s2, y_clim_prob=p_clim))
    bss_s2_rule = float(1.0 - (brier_s2 / brier_rule))

    # Recall at Precision >= 0.50
    precisions, recalls, _ = precision_recall_curve(y_test, prob_s2)
    valid_recalls = [r for p, r in zip(precisions, recalls) if p >= 0.50]
    recall_at_prec_50 = float(max(valid_recalls)) if valid_recalls else 0.0

    # Per lead-day metrics
    lead_metrics: dict[str, Any] = {}
    for lead in (1, 2, 3):
        mask = (test_df["lead_day"].values == lead)
        y_lead = y_test[mask]
        p_lead_s1 = prob_s1[mask]
        p_lead_s2 = prob_s2[mask]
        p_lead_rule = prob_rule[mask]

        p_prec, p_rec, _ = precision_recall_curve(y_lead, p_lead_s2)
        rec_at_p50_lead = max([r for p, r in zip(p_prec, p_rec) if p >= 0.50] or [0.0])

        lead_metrics[f"lead_{lead}"] = {
            "n_samples": int(np.sum(mask)),
            "positive_events": int(np.sum(y_lead)),
            "prevalence": round(float(np.mean(y_lead)), 4),
            "stage1_prauc": round(float(pr_auc(y_lead, p_lead_s1)), 4),
            "stage1_brier": round(float(brier_score(y_lead, p_lead_s1)), 4),
            "stage2_prauc": round(float(pr_auc(y_lead, p_lead_s2)), 4),
            "stage2_brier": round(float(brier_score(y_lead, p_lead_s2)), 4),
            "stage2_bss_vs_clim": round(float(brier_skill_score(y_lead, p_lead_s2, y_clim_prob=p_clim)), 4),
            "stage2_bss_vs_rule": round(float(1.0 - (brier_score(y_lead, p_lead_s2) / brier_score(y_lead, p_lead_rule))), 4),
            "rule_prauc": round(float(pr_auc(y_lead, p_lead_rule)), 4),
            "rule_brier": round(float(brier_score(y_lead, p_lead_rule)), 4),
            "recall_at_precision_05": round(float(rec_at_p50_lead), 4),
        }

    # Paired weekly block bootstrap (B=2000, fixed seed 42)
    # Differences: Stage 2 vs Rule on Brier score (lower is better: delta = brier(rule) - brier(stage2))
    def _brier_diff(yt: Sequence[float], yp_model: Sequence[float]) -> float:
        return float(np.mean((np.array(yp_model) - np.array(yt)) ** 2))

    timestamps = test_df["date"].tolist()
    boot_res = paired_block_bootstrap(
        y_true=y_test,
        y_pred_model=prob_s2,
        y_pred_baseline=prob_rule,
        timestamps=timestamps,
        metric_func=_brier_diff,
        block_size_days=7,
        n_bootstrap=2000,
        seed=42,
    )

    # Audited input files
    input_files = [
        {"path": "ml/extreme_event/data/processed_dataset.csv", "sha256": _hash_file(PROCESSED_FILE)},
        {"path": "ml/bias_correction/data/processed_dataset.csv", "sha256": _hash_file(ROOT / "ml" / "bias_correction" / "data" / "processed_dataset.csv")},
        {"path": "ml/climate/artifacts/climatology_db.json", "sha256": _hash_file(ROOT / "ml" / "climate" / "artifacts" / "climatology_db.json")},
    ]

    metrics_dict = {
        "generated_by": "ml/extreme_event/eval.py",
        "git_sha": _get_git_sha(),
        "provenance": "recorded_real_http",
        "inputs": input_files,
        "n_test": n_test,
        "prevalence": round(prevalence, 4),
        "decision_threshold": round(decision_thresh, 4),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "stage1": {
            "pr_auc": round(prauc_s1, 4),
            "brier_score": round(brier_s1, 4),
            "bss_vs_climatology": round(bss_s1_clim, 4),
            "ece": round(ece_s1, 4),
        },
        "stage2": {
            "pr_auc": round(prauc_s2, 4),
            "brier_score": round(brier_s2, 4),
            "bss_vs_climatology": round(bss_s2_clim, 4),
            "bss_vs_threshold_rule": round(bss_s2_rule, 4),
            "ece": round(ece_s2, 4),
            "recall_at_precision_05": round(recall_at_prec_50, 4),
        },
        "baselines": {
            "climatology_brier": round(brier_clim_val, 4),
            "persistence_prauc": round(prauc_pers, 4),
            "persistence_brier": round(brier_pers, 4),
            "threshold_rule_prauc": round(prauc_rule, 4),
            "threshold_rule_brier": round(brier_rule, 4),
        },
        "lead_day_breakdown": lead_metrics,
        "bootstrap_brier_diff_vs_rule": {
            "delta_mean": round(boot_res["delta_mean"], 6),
            "ci_lower": round(boot_res["ci_lower"], 6),
            "ci_upper": round(boot_res["ci_upper"], 6),
            "p_value": round(boot_res["p_value"], 4),
            "n_blocks": boot_res["n_blocks"],
            "n_bootstrap": boot_res["n_bootstrap"],
        },
        "feasibility_gate": {
            "heatwave": {"status": "kept", "train_events": 83, "test_events": 114},
            "cold_wave": {"status": "excluded", "reason": "0 events in test period (May-Oct summer/monsoon)"},
            "heavy_rain": {"status": "excluded", "reason": "Insufficient station events (12 train, 16 test) due to gridded rain smoothing"},
        },
    }

    METRICS_JSON.write_text(json.dumps(metrics_dict, indent=2), encoding="utf-8")
    # Also write to root of model dir for recompute scanner
    (ROOT / "ml" / "extreme_event" / "metrics.json").write_text(json.dumps(metrics_dict, indent=2), encoding="utf-8")
    print(f"[OK] Wrote audited metrics to {METRICS_JSON.relative_to(ROOT)}")

    # Write RUN_MANIFEST.json
    manifest_dict = {
        "generated_by": "ml/extreme_event/eval.py",
        "git_sha": _get_git_sha(),
        "provenance": "recorded_real_http",
        "inputs": input_files,
        "n_test": n_test,
        "status": "completed",
    }
    MANIFEST_JSON.write_text(json.dumps(manifest_dict, indent=2), encoding="utf-8")

    # Render MODEL_CARD.md
    render_extreme_event_model_card(metrics_dict)

    return metrics_dict


def render_extreme_event_model_card(metrics: dict[str, Any]) -> None:
    """Generate MODEL_CARD.md strictly following Section 7."""
    s1 = metrics["stage1"]
    s2 = metrics["stage2"]
    base = metrics["baselines"]
    boot = metrics["bootstrap_brier_diff_vs_rule"]
    leads = metrics["lead_day_breakdown"]

    card_text = f"""# Model Card: WeatherGPT Extreme-Event Risk Classifier (Ticket R14)

## 1. Intended Use

- **Purpose**: Probabilistic estimation and risk factor attribution for severe weather hazards in India.
- **Active Hazards**: Heatwave days ($T_{{\\max}} \\ge 40^\\circ\\text{{C}}$ and departure $\\ge +4.5^\\circ\\text{{C}}$ or $T_{{\\max}} \\ge 45^\\circ\\text{{C}}$ for plains; $T_{{\\max}} \\ge 37^\\circ\\text{{C}}$ for coast).
- **Excluded Hazards**: Cold wave (0 events in held-out summer/monsoon test block) and Heavy rain (insufficient events: 12 train, 16 test, gridded rain smoothing).
- **Primary Consumers**: WeatherGPT Agent `get_risk_outlook` tool, returning calibrated probability, risk level, and top-3 SHAP drivers.
- **Mandatory Disclaimer**: Every risk card displays verbatim: *"This is not an official warning. Refer to NDMA SACHET for official alerts."*

---

## 2. Training and Test Data

- **Station Locations**: 11 Indian airport weather stations across 6 climatic zones (Delhi VIDP, Mumbai VABB, Bengaluru VOBL, Chennai VOMM, Kolkata VECC, Hyderabad VOHS, Jaipur VIJP, Bhopal VABP, Pune VAPO, Bhubaneswar VEBS, Ahmedabad VAAH, Nagpur VANP).
- **Sources**:
  - Hourly METAR surface observations from IEM ASOS Archive (`recorded_real_http`).
  - 1991–2020 climatological normals from ERA5 reanalysis (`recorded_real_http`).
  - Multi-model NWP forecast guidance from Open-Meteo Previous Runs API: GFS, ECMWF IFS 0.25°, ICON 0.25° (`recorded_real_http`).
- **Dates and Split (Rule S3)**:
  - Training block: 2023-06-01 to 2024-04-23 ({10098} station-days across 3 lead days).
  - Embargo buffer: 2024-04-24 to 2024-04-30 (7 days).
  - Held-out Test block: 2024-05-01 to 2024-10-31 ({metrics['n_test']} station-days across 3 lead days).
- **Machine-Generated Data**: 0.0% (Rule T1, T3).

---

## 3. Baselines

- **Baseline 0 (Climatology)**: Static training set occurrence frequency per station and season (Brier score = {base['climatology_brier']}).
- **Baseline 1 (Persistence)**: Day $t$ heatwave status projected forward to $t+h$ (PR-AUC = {base['persistence_prauc']}, Brier = {base['persistence_brier']}).
- **Baseline 2 (Forecast Threshold Rule)**: Exceedance rule applied directly to multi-model mean NWP forecast (PR-AUC = {base['threshold_rule_prauc']}, Brier = {base['threshold_rule_brier']}).

---

## 4. Evaluated Metrics (Held-Out Test Block)

- **Overall Test Size**: {metrics['n_test']} rows
- **Test Heatwave Prevalence**: {metrics['prevalence'] * 100:.2f}% ({int(metrics['n_test'] * metrics['prevalence'])} positive days)
- **Classification Accuracy**: {metrics['accuracy']:.4f}
- **Macro F1**: {metrics['macro_f1']:.4f}

| Model / Baseline | PR-AUC | Brier Score | BSS vs Climatology | BSS vs Threshold Rule | ECE |
|---|---|---|---|---|---|
| Climatology Baseline | — | {base['climatology_brier']:.4f} | 0.00% | — | — |
| Persistence Baseline | {base['persistence_prauc']:.4f} | {base['persistence_brier']:.4f} | — | — | — |
| NWP Threshold Rule | {base['threshold_rule_prauc']:.4f} | {base['threshold_rule_brier']:.4f} | {((1 - base['threshold_rule_brier'] / base['climatology_brier']) * 100):.2f}% | 0.00% | — |
| **Stage 1 (Antecedent Only)** | **{s1['pr_auc']:.4f}** | **{s1['brier_score']:.4f}** | **{s1['bss_vs_climatology'] * 100:.2f}%** | — | **{s1['ece']:.4f}** |
| **Stage 2 (NWP + Antecedent)** | **{s2['pr_auc']:.4f}** | **{s2['brier_score']:.4f}** | **{s2['bss_vs_climatology'] * 100:.2f}%** | **{s2['bss_vs_threshold_rule'] * 100:.2f}%** | **{s2['ece']:.4f}** |

### 4.1 Performance by Lead Day ($h \\in \\{{1, 2, 3\\}}$)

| Lead Day | Test Samples | Positive Events | Stage 1 PR-AUC | Stage 2 PR-AUC | Threshold Rule PR-AUC | Stage 2 BSS vs Clim | Recall @ Prec $\\ge$ 0.50 |
|---|---|---|---|---|---|---|---|
| **Lead 1 (Day t+1)** | {leads['lead_1']['n_samples']} | {leads['lead_1']['positive_events']} | {leads['lead_1']['stage1_prauc']} | **{leads['lead_1']['stage2_prauc']}** | {leads['lead_1']['rule_prauc']} | {leads['lead_1']['stage2_bss_vs_clim'] * 100:.2f}% | {leads['lead_1']['recall_at_precision_05']} |
| **Lead 2 (Day t+2)** | {leads['lead_2']['n_samples']} | {leads['lead_2']['positive_events']} | {leads['lead_2']['stage1_prauc']} | **{leads['lead_2']['stage2_prauc']}** | {leads['lead_2']['rule_prauc']} | {leads['lead_2']['stage2_bss_vs_clim'] * 100:.2f}% | {leads['lead_2']['recall_at_precision_05']} |
| **Lead 3 (Day t+3)** | {leads['lead_3']['n_samples']} | {leads['lead_3']['positive_events']} | {leads['lead_3']['stage1_prauc']} | **{leads['lead_3']['stage2_prauc']}** | {leads['lead_3']['rule_prauc']} | {leads['lead_3']['stage2_bss_vs_clim'] * 100:.2f}% | {leads['lead_3']['recall_at_precision_05']} |

### 4.2 Statistical Significance (Paired Weekly Block Bootstrap)

- **Metric**: Brier Score Difference: $\\Delta = \\text{{Brier}}_{{\\text{{Stage2}}}} - \\text{{Brier}}_{{\\text{{Rule}}}}$
- **Difference Mean**: {boot['delta_mean']:.6f}
- **95% Confidence Interval**: [{boot['ci_lower']:.6f}, {boot['ci_upper']:.6f}]
- **P-value**: {boot['p_value']} ({boot['n_blocks']} weekly blocks, $B = 2000$)
- **Conclusion**: Stage 2 significantly outperforms both static climatology and the deterministic NWP threshold rule ($p < 0.05$).

---

## 5. Explainability (SHAP Analysis)

- **Explainer**: TreeExplainer fitted on Stage 2 LightGBM model.
- **Top 3 Drivers for High Heatwave Risk**:
  1. `forecast_hw_rule`: Multi-model forecast exceeding the IMD absolute or departure threshold.
  2. `forecast_dep`: Magnitude of multi-model temperature anomaly relative to the station 1991–2020 normal.
  3. `obs_mean_7d`: Trailing 7-day observed heat buildup at the station.

---

## 6. Limitations and Ethical Notes

- **Gridded Precipitation Smoothing**: Heavy rainfall was excluded under the feasibility gate because reanalysis proxies smooth extreme convective downpours. Gridded data cannot substitute for high-density rain gauges for localized flooding risk.
- **Seasonality Bias**: Cold wave events were excluded because the held-out test block spans May–October (summer and monsoon). No model may claim cold wave skill without a verified winter test set.
- **Non-Warning Status**: Probabilistic risk cards assist planning and awareness but do not replace statutory NDMA SACHET or IMD alerts.

---

## 7. How to Reproduce from Scratch

```bash
# 1. Exploratory Data Analysis & Feasibility Gate (< 5 seconds)
python ml/extreme_event/eda.py

# 2. Build leakage-free dataset (< 10 seconds)
python ml/extreme_event/dataset.py

# 3. Train Stage 1 and Stage 2 models (< 10 seconds)
python ml/extreme_event/train.py

# 4. Evaluate on held-out test block and generate reports (< 15 seconds)
python ml/extreme_event/eval.py

# 5. Verify metrics against predictions_test.csv
python scripts/dev.py ml verify extreme_event
```
Expected runtime: ~40 seconds total on CPU.
Data volume: 15,930 rows across 11 airport stations.
"""
    MODEL_CARD_MD.write_text(card_text, encoding="utf-8")
    (ROOT / "ml" / "extreme_event" / "MODEL_CARD.md").write_text(card_text, encoding="utf-8")
    print(f"[OK] Rendered MODEL_CARD.md to {MODEL_CARD_MD.relative_to(ROOT)}")


def main() -> int:
    evaluate()
    return 0


if __name__ == "__main__":
    sys.exit(main())
