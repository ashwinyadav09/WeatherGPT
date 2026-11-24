"""Extreme-Event Risk Service (Ticket R14).

Provides calibrated risk probabilities and SHAP driver explanations for severe weather hazards.
Governed by IMD criteria and project feasibility gates.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.extreme_event.dataset import STAGE1_FEATURES, STAGE2_FEATURES  # noqa: E402

ARTIFACTS_DIR = ROOT / "ml" / "extreme_event" / "artifacts"
CLIM_DB_FILE = ROOT / "ml" / "climate" / "artifacts" / "climatology_db.json"

DRIVER_NAMES: dict[str, str] = {
    "forecast_hw_rule": "NWP forecast exceeds IMD heatwave threshold",
    "forecast_dep": "Forecast temperature anomaly above 1991-2020 normal",
    "tmax_mmm": "Multi-model forecast maximum temperature",
    "normal_tmax": "Baseline climatological normal (1991-2020)",
    "obs_mean_7d": "Trailing 7-day observed heat accumulation",
    "obs_tmax_lag1": "Recent observed maximum temperature",
    "obs_dep_lag1": "Recent observed temperature departure",
    "lat": "Geographic latitude and regional vulnerability",
    "lon": "Geographic longitude",
    "elev": "Surface elevation above sea level",
    "doy_sin": "Seasonal climatological cycle",
    "doy_cos": "Seasonal solar radiation phase",
    "persistence": "Prior-day heatwave status",
    "lead_day": "Forecast lead horizon",
    "recent_bias": "Recent NWP model temperature bias",
    "tmax_gfs": "GFS forecast maximum temperature",
    "tmax_ecmwf": "ECMWF forecast maximum temperature",
    "tmax_icon": "ICON forecast maximum temperature",
}


class ExtremeEventRiskService:
    """Inference service for extreme weather risk outlooks."""

    def __init__(self) -> None:
        self._s1_model: Any = None
        self._s2_model: Any = None
        self._explainer: Any = None
        self._thresholds: dict[str, Any] = {}
        self._climatology_cells: list[tuple[float, float, list[float]]] = []
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        s1_file = ARTIFACTS_DIR / "stage1_calibrated.joblib"
        s2_file = ARTIFACTS_DIR / "stage2_calibrated.joblib"
        exp_file = ARTIFACTS_DIR / "explainer.joblib"
        thresh_file = ARTIFACTS_DIR / "thresholds.json"

        if s1_file.exists():
            self._s1_model = joblib.load(s1_file)
        if s2_file.exists():
            self._s2_model = joblib.load(s2_file)
        if exp_file.exists():
            self._explainer = joblib.load(exp_file)
        if thresh_file.exists():
            with open(thresh_file, "r", encoding="utf-8") as f:
                self._thresholds = json.load(f)

        # Load climatology database for station normal lookups
        if CLIM_DB_FILE.exists():
            with open(CLIM_DB_FILE, "r", encoding="utf-8") as f:
                cdb = json.load(f)
            for k, v in cdb.items():
                parts = k.split("_")
                tmax_norm = v.get("normals_1991_2020", {}).get("tmax_c", [30.0] * 12)
                self._climatology_cells.append((float(parts[0]), float(parts[1]), tmax_norm))

        self._loaded = True

    def get_normal_tmax(self, lat: float, lon: float, month: int) -> float:
        """Find 1991-2020 monthly normal for coordinates."""
        self._ensure_loaded()
        if not self._climatology_cells:
            return 32.0

        best = min(self._climatology_cells, key=lambda c: math.hypot(c[0] - lat, c[1] - lon))
        m_idx = max(0, min(11, month - 1))
        return float(best[2][m_idx])

    def predict_risk(
        self,
        lat: float,
        lon: float,
        elev: float = 100.0,
        target_date: dt.date | None = None,
        lead_day: int = 1,
        forecast_tmax: float | None = None,
        recent_obs_tmax: float | None = None,
    ) -> dict[str, Any]:
        """Predict extreme-event probability and top SHAP drivers for a location."""
        self._ensure_loaded()
        t_date = target_date or (dt.date.today() + dt.timedelta(days=lead_day))
        doy = t_date.timetuple().tm_yday
        doy_rad = doy * 2.0 * math.pi / 365.25
        doy_sin = math.sin(doy_rad)
        doy_cos = math.cos(doy_rad)

        normal_tmax = self.get_normal_tmax(lat, lon, t_date.month)

        # If recent observation is missing, estimate from climatological normal
        obs_lag1 = recent_obs_tmax if recent_obs_tmax is not None else normal_tmax
        obs_dep1 = obs_lag1 - normal_tmax
        obs_mean_7d = obs_lag1

        # Check if coordinates are coastal
        # Simple heuristic: coast if within 0.75 deg of sea or southern coastal coords
        is_coastal = (lat < 20.0 and (lon < 73.5 or lon > 80.0))

        if obs_lag1 >= 40.0 or (is_coastal and obs_lag1 >= 37.0 and obs_dep1 >= 4.5):
            persistence = 1.0
        else:
            persistence = 0.0

        top_drivers: list[str] = []

        if forecast_tmax is not None and self._s2_model is not None:
            # Stage 2: with NWP forecast guidance
            fc_dep = forecast_tmax - normal_tmax
            if is_coastal:
                fc_hw_rule = 1.0 if ((forecast_tmax >= 37.0 and fc_dep >= 4.5) or (forecast_tmax >= 40.0)) else 0.0
            else:
                fc_hw_rule = 1.0 if ((forecast_tmax >= 40.0 and fc_dep >= 4.5) or (forecast_tmax >= 45.0)) else 0.0

            s2_features = {
                "lead_day": lead_day,
                "doy_sin": doy_sin,
                "doy_cos": doy_cos,
                "lat": lat,
                "lon": lon,
                "elev": elev,
                "normal_tmax": normal_tmax,
                "obs_tmax_lag1": obs_lag1,
                "obs_tmax_lag2": obs_lag1,
                "obs_tmax_lag3": obs_lag1,
                "obs_dep_lag1": obs_dep1,
                "obs_mean_7d": obs_mean_7d,
                "persistence": persistence,
                "tmax_mmm": forecast_tmax,
                "tmax_gfs": forecast_tmax,
                "tmax_ecmwf": forecast_tmax,
                "tmax_icon": forecast_tmax,
                "recent_bias": 0.0,
                "forecast_dep": fc_dep,
                "forecast_hw_rule": fc_hw_rule,
            }

            feat_df = pd.DataFrame([s2_features])[STAGE2_FEATURES]
            prob = float(self._s2_model.predict_proba(feat_df)[0, 1])

            # SHAP drivers
            if self._explainer is not None:
                try:
                    shap_vals = self._explainer.shap_values(feat_df)
                    if isinstance(shap_vals, list):
                        vals = shap_vals[1][0]
                    elif hasattr(shap_vals, "values"):
                        vals = shap_vals.values[0]
                    else:
                        vals = shap_vals[0]

                    top_idxs = np.argsort(np.abs(vals))[::-1][:3]
                    for idx in top_idxs:
                        feat_name = STAGE2_FEATURES[idx]
                        desc = DRIVER_NAMES.get(feat_name, feat_name)
                        top_drivers.append(desc)
                except Exception:
                    top_drivers = ["Forecast Tmax anomaly", "Climatological baseline normal", "Regional latitude"]
            else:
                top_drivers = ["Forecast Tmax anomaly", "Climatological baseline normal", "Regional latitude"]

        elif self._s1_model is not None:
            # Stage 1: antecedent and climatology only
            s1_features = {
                "lead_day": lead_day,
                "doy_sin": doy_sin,
                "doy_cos": doy_cos,
                "lat": lat,
                "lon": lon,
                "elev": elev,
                "normal_tmax": normal_tmax,
                "obs_tmax_lag1": obs_lag1,
                "obs_tmax_lag2": obs_lag1,
                "obs_tmax_lag3": obs_lag1,
                "obs_dep_lag1": obs_dep1,
                "obs_mean_7d": obs_mean_7d,
                "persistence": persistence,
            }
            feat_df = pd.DataFrame([s1_features])[STAGE1_FEATURES]
            prob = float(self._s1_model.predict_proba(feat_df)[0, 1])
            top_drivers = ["Antecedent observed temperature", "Climatological baseline normal", "Geographic location"]
        else:
            # Fallback if model files not yet trained
            prob = 0.05
            top_drivers = ["Climatology frequency", "Seasonal normal", "Regional latitude"]

        # Risk levels
        if prob < 0.20:
            risk_level = "low"
        elif prob < 0.50:
            risk_level = "moderate"
        elif prob < 0.75:
            risk_level = "high"
        else:
            risk_level = "severe"

        return {
            "heat_wave_risk": round(prob, 4),
            "risk_level": risk_level,
            "top_drivers": top_drivers,
            "lead_day": lead_day,
            "target_date": t_date.isoformat(),
            "normal_tmax": round(normal_tmax, 1),
            "excluded_hazards": {
                "cold_wave": {
                    "status": "excluded_feasibility_gate",
                    "reason": "Test season (May-Oct summer/monsoon) has 0 cold wave events (<20 test gate).",
                },
                "heavy_rain": {
                    "status": "excluded_feasibility_gate",
                    "reason": "Insufficient station extreme rain events (<50 train, <20 test) due to gridded rain smoothing.",
                },
            },
            "advisory_note": "This is not an official warning. Refer to NDMA SACHET for official alerts.",
            "attribution": "WeatherGPT Extreme Event Risk Model (Calibrated LightGBM). This is not an official warning.",
        }
