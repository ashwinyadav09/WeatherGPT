# Extreme-Event Risk Classification (Ticket R14)

Probabilistic estimation and SHAP feature attribution for extreme weather hazards in India,
governed by published IMD station criteria and empirical feasibility gates.

## Models and Approach

- **Stage 1 (Antecedent Observations Only)**: Calibrated LightGBM model utilizing past 7-day observed temperatures, departures from 1991–2020 climatology, station coordinates, and seasonal cycle.
- **Stage 2 (NWP Forecast Guidance + Antecedent)**: Calibrated LightGBM model fusing Stage 1 features with multi-model NWP forecast guidance (GFS, ECMWF IFS, ICON) from Open-Meteo Previous Runs API.
- **Explainability**: SHAP TreeExplainer extracting top 3 feature drivers for every prediction.
- **Calibration**: Platt scaling (sigmoid calibration) producing empirical reliability.
- **Feasibility Gate**: Excludes hazards with < 50 train or < 20 test events. Heatwave is kept; cold wave and heavy rain are honestly excluded with reasons documented in `reports/eda.md`.

## Reproduce From Scratch

Exact commands to reproduce the dataset, models, and evaluation:

```bash
# 1. Exploratory Data Analysis & Feasibility Gate
python ml/extreme_event/eda.py

# 2. Build feature dataset (zero temporal leakage)
python ml/extreme_event/dataset.py

# 3. Train Stage 1, Stage 2 models, and SHAP explainer
python ml/extreme_event/train.py

# 4. Evaluate on held-out test block and generate reports
python ml/extreme_event/eval.py

# 5. Verify headline metrics against predictions_test.csv
python scripts/dev.py ml verify extreme_event

# 6. Audit all result files
python scripts/dev.py audit-results
```

- **Expected Runtime**: ~40 seconds total on CPU.
- **Data Volume**: 15,930 rows across 11 airport stations.
- **Chronological Split**: Train (2023-06-01 to 2024-04-23), 7-day Embargo (2024-04-24 to 2024-04-30), Test (2024-05-01 to 2024-10-31).
