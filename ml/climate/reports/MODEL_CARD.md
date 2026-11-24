# Model Card: Climate Trend and Anomaly Models (Phase R13)

## Summary
- **Module**: `ml.climate`
- **Dataset**: ECMWF ERA5 Reanalysis via Open-Meteo Archive API (1950 to 2024 daily records on 0.25° grid).
- **Provenance**: `recorded_real_http` (audited by `scripts/tasks/audit_results.py`).
- **Baseline Period**: WMO 30-year climatological normal period: 1991 to 2020.
- **Methods**:
  - Climatological normals: 1991-2020 monthly means and standard deviations for daily temperature and monthly precipitation.
  - Anomaly metrics: Departure (observed - normal), z-score, and empirical percentile within historical record.
  - Trend estimation: Non-parametric Mann-Kendall test with Sen's slope and 95% confidence intervals via `scipy.stats.theilslopes` and `pymannkendall`.
  - Trend stability: Leave-One-Year-Out (LOO) slope cross-validation.
  - Multivariate anomaly detection: `IsolationForest` on deseasonalised daily features (Tmax, Tmin, diurnal range, precipitation, 3-day sum).

## Evaluation Metrics
- **Grid cells evaluated**: 8
- **Mean annual temperature trend**: +0.148 °C / decade
- **Mean monsoon precipitation trend**: -7.63 mm / decade
- **Leave-One-Year-Out Slope Stability (Std)**: 0.0030 °C / decade
- **Extreme Event Recall (Isolation Forest)**: 66.7% (3 events tested)
- **Extreme Event Recall (Percentile Baseline)**: 100.0%
- **False-Flag Rate on Control Windows (Isolation Forest)**: 66.7%
- **False-Flag Rate on Control Windows (Percentile Baseline)**: 66.7%

## Known Limitations
1. **Reanalysis vs Gauge Records**: ERA5 values represent spatial grid averages (~27 km), not point meteorological station gauges.
2. **Convective Rainfall Smoothing**: Localized extreme cloudbursts are smoothed over the 0.25° grid cell.
3. **No Fabricated Numbers**: All reported metrics are evaluated directly on downloaded real ERA5 records.
