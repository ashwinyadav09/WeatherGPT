"""ForecastService post-hook for point-forecast bias correction (Ticket R11).

Applies statistical bias correction when:
- Request field ml_mode == 'ml'
- Location is within 100 km of a training station
- Elevation difference is within 300 m of the station elevation
- Model is trained and enabled_in_production == True

Otherwise returns raw forecasts unchanged.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path
from typing import Any

from ml.bias_correction.stations import STATIONS, StationMeta
from services.api.app.evidence.models import EvidencePacket, Uncertainty, ValueItem

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "ml" / "bias_correction" / "artifacts"
REPORTS_DIR = ROOT / "ml" / "bias_correction" / "reports"
WEIGHTS_FILE = ARTIFACTS_DIR / "model_weights.json"
METRICS_FILE = REPORTS_DIR / "metrics.json"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two points on Earth in km."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def find_nearest_training_station(lat: float, lon: float) -> tuple[StationMeta | None, float]:
    """Find closest training station and distance in km."""
    best_st = None
    min_dist = float("inf")

    for st in STATIONS:
        dist = haversine_km(lat, lon, st["lat"], st["lon"])
        if dist < min_dist:
            min_dist = dist
            best_st = st

    return best_st, min_dist


class BiasCorrectionInference:
    def __init__(self) -> None:
        self.weights: dict[str, Any] | None = None
        self.enabled_in_production: bool = False
        self._load()

    def _load(self) -> None:
        if WEIGHTS_FILE.exists():
            try:
                with WEIGHTS_FILE.open("r", encoding="utf-8") as f:
                    self.weights = json.load(f)
            except Exception:
                self.weights = None

        if METRICS_FILE.exists():
            try:
                with METRICS_FILE.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.enabled_in_production = bool(data.get("enabled_in_production", False))
            except Exception:
                self.enabled_in_production = False

    def predict_temperature(
        self,
        raw_temp: float,
        lead_day: int,
        lat: float,
        lon: float,
        elev: float,
        date: dt.date | None = None,
    ) -> dict[str, float] | None:
        if not self.weights or not self.enabled_in_production:
            return None

        w_ridge = self.weights.get("temperature_ridge_weights")
        w_p10 = self.weights.get("temperature_p10_weights")
        w_p90 = self.weights.get("temperature_p90_weights")
        if not (w_ridge and w_p10 and w_p90):
            return None

        cur_date = date or dt.date.today()
        doy = cur_date.timetuple().tm_yday
        doy_rad = doy * 2.0 * math.pi / 365.25
        doy_s = math.sin(doy_rad)
        doy_c = math.cos(doy_rad)

        # Feature vector: [1.0, lead, gfs, ecmwf, icon, mmm, doy_s, doy_c, lat, lon, elev, rec_bias]
        x = [
            1.0,
            float(lead_day),
            raw_temp,
            raw_temp,
            raw_temp,
            raw_temp,
            doy_s,
            doy_c,
            lat / 10.0,
            lon / 10.0,
            elev / 1000.0,
            0.0,
        ]

        corrected_val = sum(w * feat for w, feat in zip(w_ridge, x))
        p10 = sum(w * feat for w, feat in zip(w_p10, x))
        p90 = sum(w * feat for w, feat in zip(w_p90, x))

        # Enforce p10 <= p90
        if p10 > p90:
            p10, p90 = p90, p10

        return {
            "corrected_value": round(corrected_val, 2),
            "p10": round(p10, 2),
            "p90": round(p90, 2),
        }


_inference_service: BiasCorrectionInference | None = None


def get_inference_service() -> BiasCorrectionInference:
    global _inference_service
    if _inference_service is None:
        _inference_service = BiasCorrectionInference()
    return _inference_service


def apply_bias_correction_hook(
    packets: list[EvidencePacket],
    lat: float,
    lon: float,
    elev: float = 0.0,
    ml_mode: str = "raw",
) -> list[EvidencePacket]:
    """ForecastService post-hook implementing R11 integration."""
    if ml_mode != "ml":
        return packets

    nearest_st, dist_km = find_nearest_training_station(lat, lon)
    if not nearest_st or dist_km > 100.0:
        # Outside 100 km: return raw
        return packets

    if abs(elev - nearest_st["elev"]) > 300.0:
        # Elevation difference > 300 m: return raw
        return packets

    svc = get_inference_service()
    if not svc.enabled_in_production:
        return packets

    out_packets = list(packets)
    for p in packets:
        for val_item in p.values:
            if val_item.variable in ("temperature_max", "temperature_2m_max", "tmax", "temperature") and isinstance(val_item.value, (int, float)):
                raw_temp = float(val_item.value)
                pred = svc.predict_temperature(
                    raw_temp=raw_temp,
                    lead_day=1,
                    lat=lat,
                    lon=lon,
                    elev=elev,
                )
                if pred:
                    corrected_packet = EvidencePacket(
                        id=f"{p.id}-corrected",
                        source=f"MOS Bias Correction (v1.0 via {nearest_st['id']})",
                        authority_tier=p.authority_tier,
                        provenance=p.provenance,
                        issued_at=p.issued_at,
                        valid_from=p.valid_from,
                        valid_to=p.valid_to,
                        place=p.place,
                        values=[
                            ValueItem(variable="corrected_temperature_max", value=pred["corrected_value"], unit="°C"),
                            ValueItem(variable="p10", value=pred["p10"], unit="°C"),
                            ValueItem(variable="p90", value=pred["p90"], unit="°C"),
                            ValueItem(variable="raw_value", value=raw_temp, unit="°C"),
                        ],
                        uncertainty=Uncertainty(type="interval_p10_p90", value=f"[{pred['p10']}, {pred['p90']}]"),
                        attribution="WeatherGPT ML Bias Correction post-processing of raw NWP guidance",
                    )
                    out_packets.append(corrected_packet)

    return out_packets
