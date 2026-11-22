> [!CAUTION]
> **UNVERIFIED: generated from simulated data. Do not cite.**
> Archived 2026-11-22 (R0.2). See docs/archive/unverified/README.md.

---
# Model Card: Point-Forecast Bias Correction (`mos-india-v1.0`)

## Model Details
- **Developer**: WeatherGPT Team (Aman)
- **Model Type**: Model Output Statistics (MOS) point-forecast bias correction and probability calibration
- **Model Version**: `mos-india-v1.0`
- **Training Window**: `2021-01-01` to `2024-12-31`
- **Target Domain**: Surface meteorological stations and aerodromes across India (VIDP Delhi, VABB Mumbai, VOBL Bengaluru, VOMM Chennai, VECC Kolkata, Pune, Jaipur, Hyderabad, etc.)
- **Licence**: CC BY 4.0 / Open Data

## Intended Use
- **Primary Use**: Reduce systematic elevation, terrain, and seasonal forecast biases in raw global model guidance (GFS 0.25°, ECMWF IFS/AIFS) for temperature and precipitation occurrence.
- **Authority Constraint**: Corrected forecasts are strictly labeled as **Model Guidance (Authority Tier 4)** and **never override official IMD forecasts or warnings (Authority Tier 1 & 2)**.
- **Gating Policy**: Corrected values are applied **only** for variables and lead times (12h, 24h, 48h, 72h) where MOS demonstrates statistically significant skill over the raw numerical weather prediction model on held-out data. For extended ranges (>120h) where statistical skill drops below raw guidance, the system falls back to uncorrected raw model output.

## Training & Evaluation Data
- **Forecast Archives**: NOAA GFS 0.25° (via dynamical.org / Open-Meteo, CC BY 4.0).
- **Ground Truth Targets**:
  - Surface observation stations: Iowa Environmental Mesonet (IEM) `IN__ASOS` METAR archive (Open Access).
  - Climate baselines: IMD gridded daily rainfall & 1991-2020 normals (IMD Research Data).
- **Time Split (No Leakage)**:
  - Training: 2021-01-01 to 2024-12-31
  - Validation: 2025-01-01 to 2025-12-31
  - Held-out Test: 2026-01-01 to 2026-11-01

## Features
- **Temperature MOS**: Raw model 2m temperature (°C), day of year sine/cosine harmonics, station elevation (km), latitude, and lead time.
- **Precipitation Calibration**: Raw model precipitation (mm), log-transformed precipitation, monsoon season indicator (June–September), and latitude.

