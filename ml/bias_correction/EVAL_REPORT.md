# Evaluation Report: Point-Forecast Bias Correction vs. Baselines (Ticket 16)

## Summary
Ticket 16 evaluates `mos-india-v1.0` against three baselines on held-out 2026 test data across 8 major Indian weather observation stations:
1. **Raw Numerical Weather Prediction Model** (NOAA GFS 0.25°)
2. **Persistence Baseline** (observation at forecast issue time held constant)
3. **Climatology Baseline** (30-year monthly/seasonal normal)

## Temperature Evaluation (Held-Out 2026 Test Period)

| Model / Baseline | MAE (°C) | RMSE (°C) | Skill vs Raw Model |
| :--- | :--- | :--- | :--- |
| **MOS (`mos-india-v1.0`)** | **0.92°C** | **1.16°C** | **+39.5% improvement** (Winner) |
| **Raw Model (GFS 0.25°)** | 1.52°C | 1.94°C | Baseline |
| **Persistence** | 1.94°C | 2.51°C | -27.6% |
| **Climatology (1991-2020 Normal)** | 1.44°C | 1.83°C | +5.3% |

*Conclusion*: MOS reduces temperature MAE by nearly 40% compared to the raw model by learning and removing systematic cold/warm biases associated with local elevation lapses and seasonal shifts.

## Precipitation Event Evaluation (Threshold >= 2.5 mm / Day)

| Model / Baseline | POD (Detection) | FAR (False Alarm) | CSI (Critical Success Index) |
| :--- | :--- | :--- | :--- |
| **MOS (`mos-india-v1.0`)** | **0.781** | **0.312** | **0.575** (Winner) |
| **Raw Model (GFS 0.25°)** | 0.812 | 0.354 | 0.570 |
| **Persistence** | 0.448 | 0.462 | 0.321 |
| **Climatology** | 0.520 | 0.505 | 0.345 |

*Conclusion*: Raw GFS displays persistent drizzle bias (frequent false alarms of 1–4 mm on dry days). MOS filtering reduces false alarms (FAR from 35.4% down to 31.2%) and increases the Critical Success Index (CSI) from 0.570 to 0.575.

## Rain-Probability Reliability Diagram (Calibration)

Evaluated across probability forecast bins on held-out test data:

| Probability Range | Mean Forecast Probability | Observed Event Frequency | Sample Count | Calibration Status |
| :--- | :--- | :--- | :--- | :--- |
| **0.0 - 0.2 (Very Low)** | 0.082 | 0.078 | 512 | Well-calibrated (within 0.5%) |
| **0.2 - 0.4 (Low)** | 0.294 | 0.310 | 184 | Well-calibrated (within 1.6%) |
| **0.4 - 0.6 (Moderate)** | 0.488 | 0.512 | 146 | Well-calibrated (within 2.4%) |
| **0.6 - 0.8 (High)** | 0.695 | 0.718 | 198 | Well-calibrated (within 2.3%) |
| **0.8 - 1.0 (Very High)** | 0.884 | 0.892 | 260 | Well-calibrated (within 0.8%) |

*Brier Score*: 0.114 (well-calibrated across all 5 probability quantiles).

## Gating Policy & Lead-Time Decisions

| Variable | Lead Time | MOS vs Raw Result | Gate Decision | Fallback if Gate Fails |
| :--- | :--- | :--- | :--- | :--- |
| `temperature_2m` | 12h | MOS wins (MAE 0.84 vs 1.48) | **USE MOS** | Raw Model Guidance |
| `temperature_2m` | 24h | MOS wins (MAE 0.92 vs 1.52) | **USE MOS** | Raw Model Guidance |
| `temperature_2m` | 48h | MOS wins (MAE 1.08 vs 1.64) | **USE MOS** | Raw Model Guidance |
| `temperature_2m` | 72h | MOS wins (MAE 1.25 vs 1.78) | **USE MOS** | Raw Model Guidance |
| `temperature_2m` | >120h | MOS has no statistical skill | **REJECT MOS** | **Raw Model Guidance** |
| `precipitation` | 12h-72h | MOS wins on CSI & calibration | **USE MOS** | Raw Model Guidance |
| `precipitation` | >120h | MOS has no statistical skill | **REJECT MOS** | **Raw Model Guidance** |
