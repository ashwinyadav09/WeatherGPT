"""Model Output Statistics (MOS) point-forecast bias correction model (Ticket 16 / R8.2).

Implements statistical correction for temperature (MAE/RMSE minimization)
and calibrated probability of precipitation (POD, FAR, CSI) on time-split data.

Hard-coded rain weights and skill table deleted per Ticket R8.2.
Real post-processing pipelines are fitted in Phase R11.
"""

from __future__ import annotations

import math
from typing import Any

from ml.bias_correction.dataset import load_time_split_dataset


class PointForecastMOSModel:
    MODEL_VERSION = "mos-india-v1.0"
    TRAINING_WINDOW = "2021-2024"

    def __init__(self) -> None:
        self.is_trained = False
        # Temperature weights: [bias, raw_temp, sin_doy, cos_doy, elev_km, lat_scale]
        self.temp_weights: list[float] = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
        # Rain logistic weights initialized empty (hard-coded weights deleted per R8.2)
        self.rain_weights: list[float] = []
        # Skill gate table initialized empty (hard-coded table deleted per R8.2)
        self.val_skill: dict[str, dict[int, bool]] = {}

    def _temp_features(self, raw_temp: float, doy: int, elev: float, lat: float) -> list[float]:
        doy_rad = doy * 2.0 * math.pi / 365.0
        return [
            1.0,
            raw_temp,
            math.sin(doy_rad),
            math.cos(doy_rad),
            elev / 1000.0,
            lat / 10.0,
        ]

    def train(self, train_data: list[dict[str, Any]] | None = None) -> None:
        """Fits MOS regression weights on the training dataset."""
        if train_data is None:
            train_data, _, _ = load_time_split_dataset()

        if not train_data:
            self.is_trained = False
            return

        # Regularized ordinary least squares for temperature MOS:
        # Solve (X^T X + lambda I) w = X^T y
        num_features = 6
        xtx = [[0.0] * num_features for _ in range(num_features)]
        xty = [0.0] * num_features

        for row in train_data:
            feats = self._temp_features(
                raw_temp=row["raw_temp_forecast"],
                doy=row["day_of_year"],
                elev=row["elevation"],
                lat=row["lat"],
            )
            y = row["observed_temp"]

            for i in range(num_features):
                xty[i] += feats[i] * y
                for j in range(num_features):
                    xtx[i][j] += feats[i] * feats[j]

        # Add L2 ridge regularization
        l2_reg = 0.5
        for i in range(num_features):
            xtx[i][i] += l2_reg

        # Simple 6x6 Gauss-Jordan elimination
        n = num_features
        aug = [xtx[i] + [xty[i]] for i in range(n)]

        for col in range(n):
            pivot = col
            for r in range(col + 1, n):
                if abs(aug[r][col]) > abs(aug[pivot][col]):
                    pivot = r
            aug[col], aug[pivot] = aug[pivot], aug[col]

            pivot_val = aug[col][col]
            if abs(pivot_val) > 1e-9:
                for c in range(col, n + 1):
                    aug[col][c] /= pivot_val
                for r in range(n):
                    if r != col:
                        factor = aug[r][col]
                        for c in range(col, n + 1):
                            aug[r][c] -= factor * aug[col][c]

        self.temp_weights = [aug[i][n] for i in range(n)]
        self.is_trained = True

    def predict_temperature(self, raw_temp: float, day_of_year: int, elev_m: float, lat: float) -> float:
        feats = self._temp_features(raw_temp, day_of_year, elev_m, lat)
        val = sum(w * f for w, f in zip(self.temp_weights, feats))
        return round(val, 2)

    def predict_rain_probability(self, raw_rain: float, month: int, lat: float) -> float:
        """Estimates calibrated probability of rain occurrence (>= 2.5 mm)."""
        if not self.rain_weights:
            # If rain model is not fitted, return raw proxy or baseline
            return 0.5 if raw_rain >= 2.5 else 0.05
        is_monsoon = 1.0 if 6 <= month <= 9 else 0.0
        log_rain = math.log1p(max(0.0, raw_rain))
        feats = [1.0, raw_rain, log_rain, is_monsoon, lat / 10.0]
        z = sum(w * f for w, f in zip(self.rain_weights, feats))
        prob = 1.0 / (1.0 + math.exp(-z))
        return round(min(0.98, max(0.02, prob)), 3)

    def should_use_correction(self, variable: str, lead_time_hours: int) -> bool:
        """Gate: Returns True only if MOS beats the raw model on held-out data for this variable and lead time."""
        lead_skills = self.val_skill.get(variable, {})
        return lead_skills.get(lead_time_hours, False)

    def evaluate_temperature(self, test_data: list[dict[str, Any]] | None = None) -> dict[str, dict[str, float]]:
        """Evaluates temperature MAE and RMSE against raw model, persistence, and climatology."""
        if test_data is None:
            _, _, test_data = load_time_split_dataset()

        if not test_data:
            return {
                "mos": {"mae": 0.0, "rmse": 0.0},
                "raw_model": {"mae": 0.0, "rmse": 0.0},
                "persistence": {"mae": 0.0, "rmse": 0.0},
                "climatology": {"mae": 0.0, "rmse": 0.0},
            }

        errors: dict[str, list[float]] = {
            "mos": [],
            "raw_model": [],
            "persistence": [],
            "climatology": [],
        }

        for row in test_data:
            y_true = row["observed_temp"]

            y_mos = self.predict_temperature(
                raw_temp=row["raw_temp_forecast"],
                day_of_year=row["day_of_year"],
                elev_m=row["elevation"],
                lat=row["lat"],
            )
            y_raw = row["raw_temp_forecast"]
            y_persist = row.get("persistence_temp", y_true)
            y_clim = row.get("climatology_temp", y_true)

            errors["mos"].append(y_mos - y_true)
            errors["raw_model"].append(y_raw - y_true)
            errors["persistence"].append(y_persist - y_true)
            errors["climatology"].append(y_clim - y_true)

        report = {}
        for k, errs in errors.items():
            n = len(errs)
            mae = sum(abs(e) for e in errs) / n if n > 0 else 0.0
            rmse = math.sqrt(sum(e * e for e in errs) / n) if n > 0 else 0.0
            report[k] = {"mae": round(mae, 2), "rmse": round(rmse, 2)}

        return report

    def evaluate_precipitation(self, test_data: list[dict[str, Any]] | None = None) -> dict[str, dict[str, float]]:
        """Evaluates rain event (>= 2.5 mm) POD, FAR, and CSI."""
        if test_data is None:
            _, _, test_data = load_time_split_dataset()

        if not test_data:
            return {
                "mos": {"pod": 0.0, "far": 0.0, "csi": 0.0},
                "raw_model": {"pod": 0.0, "far": 0.0, "csi": 0.0},
                "persistence": {"pod": 0.0, "far": 0.0, "csi": 0.0},
                "climatology": {"pod": 0.0, "far": 0.0, "csi": 0.0},
            }

        stats: dict[str, dict[str, int]] = {
            "mos": {"H": 0, "F": 0, "M": 0},
            "raw_model": {"H": 0, "F": 0, "M": 0},
            "persistence": {"H": 0, "F": 0, "M": 0},
            "climatology": {"H": 0, "F": 0, "M": 0},
        }

        for row in test_data:
            obs_event = row["observed_rain_event"] == 1

            prob_mos = self.predict_rain_probability(
                raw_rain=row["raw_rain_forecast"],
                month=row["month"],
                lat=row["lat"],
            )
            pred_mos = prob_mos >= 0.40
            pred_raw = row["raw_rain_forecast"] >= 2.5
            pred_persist = row.get("persistence_rain", 0.0) >= 2.5
            pred_clim = row.get("climatology_rain", 0.0) >= 4.0

            preds = {
                "mos": pred_mos,
                "raw_model": pred_raw,
                "persistence": pred_persist,
                "climatology": pred_clim,
            }

            for model_key, pred_event in preds.items():
                if pred_event and obs_event:
                    stats[model_key]["H"] += 1
                elif pred_event and not obs_event:
                    stats[model_key]["F"] += 1
                elif not pred_event and obs_event:
                    stats[model_key]["M"] += 1

        report = {}
        for k, s in stats.items():
            h, f, m = s["H"], s["F"], s["M"]
            pod = h / (h + m) if (h + m) > 0 else 0.0
            far = f / (h + f) if (h + f) > 0 else 0.0
            csi = h / (h + m + f) if (h + m + f) > 0 else 0.0
            report[k] = {
                "pod": round(pod, 3),
                "far": round(far, 3),
                "csi": round(csi, 3),
            }

        return report

    def generate_reliability_diagram(self, test_data: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Produces calibration bins of forecast probability vs observed relative frequency."""
        if test_data is None:
            _, _, test_data = load_time_split_dataset()

        bin_edges = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        bins = []

        for i in range(len(bin_edges) - 1):
            low, high = bin_edges[i], bin_edges[i + 1]
            prob_sum = 0.0
            obs_sum = 0
            count = 0

            for row in test_data:
                prob = self.predict_rain_probability(
                    raw_rain=row["raw_rain_forecast"],
                    month=row["month"],
                    lat=row["lat"],
                )
                if (i == 0 and low <= prob <= high) or (low < prob <= high):
                    prob_sum += prob
                    obs_sum += row["observed_rain_event"]
                    count += 1

            mean_prob = prob_sum / count if count > 0 else (low + high) / 2.0
            obs_freq = obs_sum / count if count > 0 else 0.0
            bins.append(
                {
                    "prob_range": f"{low:.1f}-{high:.1f}",
                    "forecast_prob": round(mean_prob, 3),
                    "observed_freq": round(obs_freq, 3),
                    "count": count,
                }
            )

        return {"bins": bins}
