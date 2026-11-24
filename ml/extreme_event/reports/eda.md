# Extreme-Event Exploratory Data Analysis and Feasibility Gate (Ticket R14)

## 1. Hazard Criteria and Published Authority Sources

Hazard definitions follow official India Meteorological Department (IMD) criteria:

- **Heatwave Day**:
  - *Authority*: India Meteorological Department (IMD), Ministry of Earth Sciences, *Criteria for Declaring Heat Wave* (URL: https://mausam.imd.gov.in/).
  - *Plains stations*: Maximum temperature $T_{\max} \ge 40.0^\circ\text{C}$ with departure $\ge +4.5^\circ\text{C}$ from 1991–2020 normal, OR actual $T_{\max} \ge 45.0^\circ\text{C}$ regardless of normal. (Severe heatwave: departure $\ge +6.5^\circ\text{C}$ or $T_{\max} \ge 47.0^\circ\text{C}$).
  - *Coastal stations*: Maximum temperature $T_{\max} \ge 37.0^\circ\text{C}$ with departure $\ge +4.5^\circ\text{C}$, OR actual $T_{\max} \ge 40.0^\circ\text{C}$.
- **Cold Wave Day**:
  - *Authority*: India Meteorological Department (IMD), *Criteria for Declaring Cold Wave*.
  - *Plains stations*: Minimum temperature $T_{\min} \le 10.0^\circ\text{C}$ with departure $\le -4.5^\circ\text{C}$ from normal, OR actual $T_{\min} \le 4.0^\circ\text{C}$.
  - *Coastal stations*: Minimum temperature $T_{\min} \le 15.0^\circ\text{C}$ with departure $\le -4.5^\circ\text{C}$.
- **Heavy Rain Day**:
  - *Authority*: India Meteorological Department (IMD), *Standard Operating Procedure for Weather Forecasting and Warning Services*.
  - *Definition*: 24-hour accumulated rainfall $R_{24} \ge 64.5\text{ mm}$ (Heavy: 64.5–115.5 mm; Very Heavy: 115.6–204.4 mm; Extremely Heavy: $\ge 204.5\text{ mm}$).

---

## 2. Feasibility Gate Results

Per Ticket R14 and project remediation rules:
> **Feasibility Gate**: Keep a hazard only if it has at least **50 positive station-days in training** (2023-06-01 to 2024-04-23) and **20 positive station-days in held-out test** (2024-05-01 to 2024-10-31). Excluded hazards must be documented honestly.

| Hazard | Training Count (Req $\ge$ 50) | Test Count (Req $\ge$ 20) | Embargo Count | Total Events | Gate Status | Decision |
|---|---|---|---|---|---|---|
| **Heatwave** | **83** | **114** | 17 | 214 | **PASS** | **KEPT for Modelling** |
| **Cold wave** | 134 | 0 | 0 | 134 | **FAIL** | **EXCLUDED (0 events in test season)** |
| **Heavy rain** | 12 | 16 | 0 | 28 | **FAIL** | **EXCLUDED (Sparse station events & grid smoothing)** |

---

## 3. Detailed Hazard Breakdown and Analysis

### 3.1 Heatwave (Kept)
- **Training Days**: 83 positive days across 11 stations (principally May–June 2023 and April 2024 in Northern Plains and Central India).
- **Test Days**: 114 positive days during the historic May–June 2024 North/Central Indian heatwave.
- **Top Heatwave Stations**:
  - Nagpur (VANP): 34 train days, 31 test days
  - Delhi (VIDP): 0 train days (METAR station QC window started post-peak in June 2023), 22 test days
  - Chennai (VOMM): 19 train days, 20 test days
  - Bhubaneswar (VEBS): 17 train days, 13 test days
  - Mumbai (VABB): 12 train days, 2 test days

### 3.2 Cold Wave (Excluded)
- **Reason for Exclusion**: The chronological test block runs from **May 1, 2024 to October 31, 2024** (spanning the Indian summer, monsoon, and early post-monsoon).
- Minimum temperatures at Indian airport stations during May through October do not drop below $10.0^\circ\text{C}$ or $4.0^\circ\text{C}$. Consequently, the test set has exactly **0 positive events**, failing the test threshold ($0 < 20$).
- Training on winter 2023–2024 without a valid winter test set violates chronological validation integrity (Rule S3). Per the feasibility gate, cold wave is honestly excluded until winter observations are available for testing.

### 3.3 Heavy Rain (Excluded)
- **Reason for Exclusion**: With daily rainfall $\ge 64.5\text{ mm}$, training contains only **12 station-days** (< 50) and test contains only **16 station-days** (< 20).
- Extreme rainfall is spatially intermittent and localized; gridded reanalysis (ERA5 proxy truth) smooths high-intensity precipitation peaks over $0.25^\circ \times 0.25^\circ$ cells. Training a classifier on 12 events would lead to severe overfitting and unreliable probability calibration.

---

## 4. Modeling Strategy for Kept Hazard (Heatwave)

- **Stage 1**: LightGBM model utilizing antecedent observations (past 7 days), seasonal harmonics (`doy_sin`, `doy_cos`), station coordinates (`lat`, `lon`, `elev`), and departure from climatology.
- **Stage 2**: LightGBM model fusing Stage 1 features with multi-model NWP forecast guidance (`tmax_mmm`, `tmax_gfs`, `tmax_ecmwf`, `tmax_icon`, `recent_bias`, forecast threshold rule).
- **Probability Calibration**: Platt scaling (`CalibratedClassifierCV(method='sigmoid')`) to produce well-calibrated probabilities.
- **Explainability**: SHAP TreeExplainer yielding the top-3 feature drivers for risk cards.
- **Card Contract**: When `get_risk_outlook` is called, heatwave probability and top drivers are returned. Excluded hazards (cold wave, heavy rain) are honestly marked absent with explanatory notes.
