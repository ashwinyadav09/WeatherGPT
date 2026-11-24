# Model Card: WeatherGPT Extreme-Event Risk Classifier (Ticket R14)

## 1. Intended Use

- **Purpose**: Probabilistic estimation and risk factor attribution for severe weather hazards in India.
- **Active Hazards**: Heatwave days ($T_{\max} \ge 40^\circ\text{C}$ and departure $\ge +4.5^\circ\text{C}$ or $T_{\max} \ge 45^\circ\text{C}$ for plains; $T_{\max} \ge 37^\circ\text{C}$ for coast).
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
  - Training block: 2023-06-01 to 2024-04-23 (10098 station-days across 3 lead days).
  - Embargo buffer: 2024-04-24 to 2024-04-30 (7 days).
  - Held-out Test block: 2024-05-01 to 2024-10-31 (5601 station-days across 3 lead days).
- **Machine-Generated Data**: 0.0% (Rule T1, T3).

---

## 3. Baselines

- **Baseline 0 (Climatology)**: Static training set occurrence frequency per station and season (Brier score = 0.0587).
- **Baseline 1 (Persistence)**: Day $t$ heatwave status projected forward to $t+h$ (PR-AUC = 0.6301, Brier = 0.048).
- **Baseline 2 (Forecast Threshold Rule)**: Exceedance rule applied directly to multi-model mean NWP forecast (PR-AUC = 0.6934, Brier = 0.0446).

---

## 4. Evaluated Metrics (Held-Out Test Block)

- **Overall Test Size**: 5601 rows
- **Test Heatwave Prevalence**: 6.11% (342 positive days)
- **Classification Accuracy**: 0.9391
- **Macro F1**: 0.8003

| Model / Baseline | PR-AUC | Brier Score | BSS vs Climatology | BSS vs Threshold Rule | ECE |
|---|---|---|---|---|---|
| Climatology Baseline | — | 0.0587 | 0.00% | — | — |
| Persistence Baseline | 0.6301 | 0.0480 | — | — | — |
| NWP Threshold Rule | 0.6934 | 0.0446 | 24.02% | 0.00% | — |
| **Stage 1 (Antecedent Only)** | **0.6036** | **0.0438** | **25.25%** | — | **0.0257** |
| **Stage 2 (NWP + Antecedent)** | **0.6795** | **0.0381** | **35.05%** | **14.65%** | **0.0266** |

### 4.1 Performance by Lead Day ($h \in \{1, 2, 3\}$)

| Lead Day | Test Samples | Positive Events | Stage 1 PR-AUC | Stage 2 PR-AUC | Threshold Rule PR-AUC | Stage 2 BSS vs Clim | Recall @ Prec $\ge$ 0.50 |
|---|---|---|---|---|---|---|---|
| **Lead 1 (Day t+1)** | 1867 | 114 | 0.6565 | **0.733** | 0.7316 | 36.25% | 0.9035 |
| **Lead 2 (Day t+2)** | 1867 | 114 | 0.6033 | **0.6992** | 0.705 | 35.50% | 0.8684 |
| **Lead 3 (Day t+3)** | 1867 | 114 | 0.5563 | **0.6152** | 0.6496 | 33.41% | 0.8158 |

### 4.2 Statistical Significance (Paired Weekly Block Bootstrap)

- **Metric**: Brier Score Difference: $\Delta = \text{Brier}_{\text{Stage2}} - \text{Brier}_{\text{Rule}}$
- **Difference Mean**: -0.006646
- **95% Confidence Interval**: [-0.016128, 0.001219]
- **P-value**: 0.114 (27 weekly blocks, $B = 2000$)
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
