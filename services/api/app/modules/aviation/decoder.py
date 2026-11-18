from __future__ import annotations

import math
import re
from typing import Any

from services.api.app.modules.aviation.models import CloudLayer, FlightCategory, WindCalculation

WEATHER_DESCRIPTIONS: dict[str, str] = {
    "HZ": "Haze",
    "BR": "Mist",
    "FG": "Fog",
    "BCFG": "Patches of Fog",
    "MIFG": "Shallow Fog",
    "DZ": "Drizzle",
    "RA": "Rain",
    "-RA": "Light Rain",
    "+RA": "Heavy Rain",
    "TS": "Thunderstorm",
    "TSRA": "Thunderstorm with Rain",
    "-TSRA": "Thunderstorm with Light Rain",
    "+TSRA": "Thunderstorm with Heavy Rain",
    "SQ": "Squall",
    "DU": "Dust",
    "SA": "Sand",
    "FU": "Smoke",
    "NSC": "Nil Significant Cloud",
    "CAVOK": "Ceiling and Visibility OK",
    "NOSIG": "No Significant Change",
}


def calculate_flight_category(visibility_meters: int, ceiling_ft: int | None) -> FlightCategory:
    """Calculates FAA / ICAO flight category based on visibility and ceiling.

    - LIFR (Low IFR): Ceiling < 500 ft AGL and/or Visibility < 1600 m (< 1 SM).
    - IFR: Ceiling 500 to < 1000 ft AGL and/or Visibility 1600 to < 5000 m (1 to < 3 SM).
    - MVFR (Marginal VFR): Ceiling 1000 to 3000 ft AGL and/or Visibility 5000 to 8000 m (3 to 5 SM).
    - VFR: Ceiling > 3000 ft AGL and Visibility > 8000 m (> 5 SM).

    Most restrictive category prevails.
    """
    # 1. Check visibility component
    if visibility_meters < 1600:
        vis_cat: FlightCategory = "LIFR"
    elif visibility_meters < 5000:
        vis_cat = "IFR"
    elif visibility_meters <= 8000:
        vis_cat = "MVFR"
    else:
        vis_cat = "VFR"

    # 2. Check ceiling component
    if ceiling_ft is None:
        ceil_cat: FlightCategory = "VFR"
    elif ceiling_ft < 500:
        ceil_cat = "LIFR"
    elif ceiling_ft < 1000:
        ceil_cat = "IFR"
    elif ceiling_ft <= 3000:
        ceil_cat = "MVFR"
    else:
        ceil_cat = "VFR"

    priority: dict[FlightCategory, int] = {"LIFR": 1, "IFR": 2, "MVFR": 3, "VFR": 4}
    return vis_cat if priority[vis_cat] <= priority[ceil_cat] else ceil_cat


def calculate_wind_components(
    runway_name: str,
    runway_heading: int,
    wind_direction: int | None,
    wind_speed_kt: float,
    wind_gust_kt: float | None = None,
) -> WindCalculation:
    """Computes crosswind and headwind/tailwind components for a specific runway.

    Formula:
    alpha = (wind_dir - rwy_heading + 180) % 360 - 180
    crosswind = |wind_speed * sin(alpha)|
    headwind = wind_speed * cos(alpha) (negative indicates tailwind)
    """
    if wind_direction is None or wind_speed_kt == 0:
        return WindCalculation(
            runway=runway_name,
            runway_heading=runway_heading,
            wind_direction=0,
            wind_speed_kt=0.0,
            wind_gust_kt=wind_gust_kt,
            relative_angle=0,
            crosswind_kt=0.0,
            crosswind_component_side="calm",
            headwind_kt=0.0,
            is_tailwind=False,
        )

    # Relative angle normalized to -180 to +180 degrees
    diff = (wind_direction - runway_heading + 180) % 360 - 180
    rad = math.radians(diff)

    crosswind = abs(wind_speed_kt * math.sin(rad))
    headwind = wind_speed_kt * math.cos(rad)

    if abs(crosswind) < 0.5:
        side: Any = "head" if headwind >= 0 else "tail"
    elif diff > 0:
        side = "right"
    else:
        side = "left"

    is_tailwind = headwind < -0.1

    return WindCalculation(
        runway=runway_name,
        runway_heading=runway_heading,
        wind_direction=wind_direction,
        wind_speed_kt=round(wind_speed_kt, 1),
        wind_gust_kt=round(wind_gust_kt, 1) if wind_gust_kt else None,
        relative_angle=diff,
        crosswind_kt=round(crosswind, 1),
        crosswind_component_side=side,
        headwind_kt=round(headwind, 1),
        is_tailwind=is_tailwind,
    )


def decode_metar_raw(raw: str) -> dict[str, Any]:
    """Decodes standard ICAO METAR syntax into structured parameters."""
    tokens = raw.strip().split()
    if not tokens:
        raise ValueError("Empty METAR text")

    # Drop leading "METAR" or "SPECI" if present
    idx = 0
    if tokens[idx] in ("METAR", "SPECI"):
        idx += 1

    station = tokens[idx] if idx < len(tokens) else "UNKNOWN"
    idx += 1

    _time_tok = tokens[idx] if idx < len(tokens) else ""
    idx += 1

    # Wind pattern: e.g. 27014KT, 24016G24KT, 00000KT, VRB02KT
    wind_dir: int | None = None
    wind_speed: float = 0.0
    wind_gust: float | None = None

    if idx < len(tokens):
        wind_m = re.match(r"^(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT$", tokens[idx])
        if wind_m:
            w_dir_raw, w_spd_raw, w_gst_raw = wind_m.groups()
            wind_dir = None if w_dir_raw == "VRB" else int(w_dir_raw)
            wind_speed = float(w_spd_raw)
            wind_gust = float(w_gst_raw) if w_gst_raw else None
            idx += 1

    # Skip variable wind direction group e.g. 210V280
    if idx < len(tokens) and re.match(r"^\d{3}V\d{3}$", tokens[idx]):
        idx += 1

    # Visibility e.g. 4000, 9999, 0800, 10SM, CAVOK
    visibility_meters = 10000
    if idx < len(tokens):
        vis_tok = tokens[idx]
        if vis_tok == "CAVOK":
            visibility_meters = 10000
            idx += 1
        elif re.match(r"^\d{4}$", vis_tok):
            visibility_meters = int(vis_tok)
            idx += 1
        elif vis_tok.endswith("SM"):
            sm_val = float(vis_tok[:-2])
            visibility_meters = int(sm_val * 1609.34)
            idx += 1

    # Weather conditions e.g. HZ, -RA, +TSRA, FG
    weather_conditions: list[str] = []
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in WEATHER_DESCRIPTIONS:
            weather_conditions.append(WEATHER_DESCRIPTIONS[tok])
            idx += 1
        elif any(tok.startswith(prefix) for prefix in ("+", "-", "VC")) and tok[1:] in WEATHER_DESCRIPTIONS:
            weather_conditions.append(WEATHER_DESCRIPTIONS.get(tok, tok))
            idx += 1
        else:
            break

    # Cloud layers e.g. NSC, FEW020, SCT030, BKN015, OVC030
    clouds: list[CloudLayer] = []
    ceiling_ft: int | None = None
    while idx < len(tokens):
        tok = tokens[idx]
        if tok in ("NSC", "SKC", "CLR", "NCD"):
            clouds.append(CloudLayer(cover=tok, base_ft=None))
            idx += 1
        else:
            c_m = re.match(r"^(FEW|SCT|BKN|OVC|VV)(\d{3})(?:CB|TCU)?$", tok)
            if c_m:
                cov, base_hundreds = c_m.groups()
                base = int(base_hundreds) * 100
                clouds.append(CloudLayer(cover=cov, base_ft=base))
                if cov in ("BKN", "OVC", "VV") and (ceiling_ft is None or base < ceiling_ft):
                    ceiling_ft = base
                idx += 1
            else:
                break

    # Temperature / Dewpoint e.g. 28/14, 29/25, M02/M05
    temperature_c = 25.0
    dewpoint_c = 15.0
    if idx < len(tokens):
        td_m = re.match(r"^(M?\d{2})/(M?\d{2})$", tokens[idx])
        if td_m:
            t_str, d_str = td_m.groups()
            temperature_c = -float(t_str[1:]) if t_str.startswith("M") else float(t_str)
            dewpoint_c = -float(d_str[1:]) if d_str.startswith("M") else float(d_str)
            idx += 1

    # QNH / Altimeter e.g. Q1012, A2992
    qnh_hpa = 1013.25
    if idx < len(tokens):
        q_m = re.match(r"^Q(\d{4})$", tokens[idx])
        if q_m:
            qnh_hpa = float(q_m.group(1))
            idx += 1
        else:
            a_m = re.match(r"^A(\d{4})$", tokens[idx])
            if a_m:
                inhg = float(a_m.group(1)) / 100.0
                qnh_hpa = round(inhg * 33.8639, 1)
                idx += 1

    flight_cat = calculate_flight_category(visibility_meters=visibility_meters, ceiling_ft=ceiling_ft)

    return {
        "station": station,
        "wind_dir": wind_dir,
        "wind_speed_kt": wind_speed,
        "wind_gust_kt": wind_gust,
        "visibility_meters": visibility_meters,
        "weather_conditions": weather_conditions,
        "clouds": clouds,
        "ceiling_ft": ceiling_ft,
        "temperature_c": temperature_c,
        "dewpoint_c": dewpoint_c,
        "qnh_hpa": qnh_hpa,
        "flight_category": flight_cat,
    }
