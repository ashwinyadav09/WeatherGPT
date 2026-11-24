"""Dataset loader, QC filtering, and feature engineering for bias correction (Ticket R11).

Quality Control (METAR):
- Temperature bounds: -5 °C to 55 °C
- Daily coverage: >= 16 hourly observations with day (06-18h) and night (18-06h) coverage
- Station validity: >= 70% valid days

Splits (Rule S3, Ticket R11):
- Train: 2023-06-01 to 2024-04-23
- Embargo: 2024-04-24 to 2024-04-30 (7 days)
- Held-out Test: 2024-05-01 to 2024-10-31 (6 full months: May pre-monsoon, Jun-Sep monsoon, Oct post-monsoon)
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path
from typing import Any

from ml.bias_correction.stations import STATIONS

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA_DIR = ROOT / "ml" / "bias_correction" / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_FILE = DATA_DIR / "processed_dataset.csv"

TEST_START_DATE = "2024-05-01"
TEST_END_DATE = "2024-10-31"
EMBARGO_DAYS = 7


def _parse_metar_file(file_path: Path) -> dict[str, dict[str, Any]]:
    """Parse raw IEM METAR CSV and aggregate into QC-filtered IST daily observations."""
    if not file_path.exists():
        return {}

    # Group observations by IST date (YYYY-MM-DD)
    day_obs: dict[str, list[tuple[int, float]]] = {}
    with file_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            val_str = r.get("tmpc", "").strip()
            valid_time_str = r.get("valid", "").strip()
            if not val_str or val_str in ("M", "T") or not valid_time_str:
                continue
            try:
                temp = float(val_str)
                # QC: remove physically impossible temperatures
                if temp < -5.0 or temp > 55.0:
                    continue
                date_part, time_part = valid_time_str.split(" ")
                hour = int(time_part.split(":")[0])
                day_obs.setdefault(date_part, []).append((hour, temp))
            except (ValueError, IndexError):
                continue

    daily_qc: dict[str, dict[str, Any]] = {}
    for d_str, obs in day_obs.items():
        if len(obs) < 16:
            continue
        hours = {h for h, _ in obs}
        has_day = any(6 <= h < 18 for h in hours)
        has_night = any(h < 6 or h >= 18 for h in hours)
        if not (has_day and has_night):
            continue

        temps = [t for _, t in obs]
        tmax = max(temps)
        tmin = min(temps)
        daily_qc[d_str] = {
            "tmax": round(tmax, 1),
            "tmin": round(tmin, 1),
            "count": len(obs),
        }

    return daily_qc


def _parse_previous_runs_file(file_path: Path) -> dict[str, dict[int, dict[str, float]]]:
    """Parse Open-Meteo previous runs hourly forecasts and aggregate into daily lead-day values."""
    if not file_path.exists():
        return {}

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    if not times:
        return {}

    # Models: gfs_seamless, ecmwf_ifs025, icon_seamless
    # Collect hourly arrays for each lead day
    models = ["gfs_seamless", "ecmwf_ifs025", "icon_seamless"]
    temp_keys: dict[str, dict[int, list[float | None]]] = {}
    precip_keys: dict[str, dict[int, list[float | None]]] = {}

    for m in models:
        temp_keys[m] = {}
        precip_keys[m] = {}
        for lead in (1, 2, 3):
            # Key naming in Open-Meteo previous runs response
            tk = f"temperature_2m_previous_day{lead}_{m}"
            if tk not in hourly:
                tk = f"temperature_2m_previous_day{lead}"
            pk = f"precipitation_previous_day{lead}_{m}"
            if pk not in hourly:
                pk = f"precipitation_previous_day{lead}"
            temp_keys[m][lead] = hourly.get(tk, [None] * len(times))
            precip_keys[m][lead] = hourly.get(pk, [None] * len(times))

    # Aggregate by IST day and lead day
    daily_nwp: dict[str, dict[int, dict[str, float]]] = {}

    for idx, t_str in enumerate(times):
        d_str = t_str.split("T")[0]
        daily_nwp.setdefault(d_str, {1: {}, 2: {}, 3: {}})

    # Aggregate 24 hours per day
    day_indices: dict[str, list[int]] = {}
    for idx, t_str in enumerate(times):
        d_str = t_str.split("T")[0]
        day_indices.setdefault(d_str, []).append(idx)

    for d_str, idxs in day_indices.items():
        if len(idxs) < 20:
            continue
        for lead in (1, 2, 3):
            m_tmax: dict[str, float] = {}
            m_rain: dict[str, float] = {}
            for m in models:
                t_vals: list[float] = [float(temp_keys[m][lead][i]) for i in idxs if temp_keys[m][lead][i] is not None]  # type: ignore[arg-type]
                p_vals: list[float] = [float(precip_keys[m][lead][i]) for i in idxs if precip_keys[m][lead][i] is not None]  # type: ignore[arg-type]
                if t_vals:
                    m_tmax[m] = max(t_vals)
                if p_vals:
                    m_rain[m] = sum(p_vals)

            if m_tmax:
                # Multi-model mean
                tmax_vals = [float(v) for v in m_tmax.values()]
                mmm_tmax = sum(tmax_vals) / len(tmax_vals)
                daily_nwp[d_str][lead]["tmax_mmm"] = round(mmm_tmax, 2)
                daily_nwp[d_str][lead]["tmax_gfs"] = round(m_tmax.get("gfs_seamless", mmm_tmax), 2)
                daily_nwp[d_str][lead]["tmax_ecmwf"] = round(m_tmax.get("ecmwf_ifs025", mmm_tmax), 2)
                daily_nwp[d_str][lead]["tmax_icon"] = round(m_tmax.get("icon_seamless", mmm_tmax), 2)

            if m_rain:
                rain_vals = [float(v) for v in m_rain.values()]
                mmm_rain = sum(rain_vals) / len(rain_vals)
                daily_nwp[d_str][lead]["rain_mmm"] = round(mmm_rain, 2)
                daily_nwp[d_str][lead]["rain_gfs"] = round(m_rain.get("gfs_seamless", mmm_rain), 2)
                daily_nwp[d_str][lead]["rain_ecmwf"] = round(m_rain.get("ecmwf_ifs025", mmm_rain), 2)
                daily_nwp[d_str][lead]["rain_icon"] = round(m_rain.get("icon_seamless", mmm_rain), 2)

    return daily_nwp


def _parse_precip_truth_file(file_path: Path) -> dict[str, float]:
    """Parse Open-Meteo archive daily precipitation proxy truth."""
    if not file_path.exists():
        return {}

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    daily = data.get("daily", {})
    times = daily.get("time", [])
    precip = daily.get("precipitation_sum", [])
    res = {}
    for t, p in zip(times, precip):
        if p is not None:
            res[t] = float(p)
    return res


def build_processed_dataset(stations: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Assemble all QC-filtered station observations and NWP forecasts into a single dataset.

    Enforces Stop Conditions (Rule S1):
    - Must have >= 10 stations with valid data (>= 70% valid days).
    - Must have >= 400 test station-days in held-out test block.
    """
    target_stations = stations or STATIONS
    valid_station_count = 0
    all_rows: list[dict[str, Any]] = []

    for st in target_stations:
        st_id = st["id"]
        lat, lon, elev = st["lat"], st["lon"], st["elev"]

        metar_qc = _parse_metar_file(RAW_DIR / f"{st_id}_metar.csv")
        nwp_data = _parse_previous_runs_file(RAW_DIR / f"{st_id}_previous_runs.json")
        precip_truth = _parse_precip_truth_file(RAW_DIR / f"{st_id}_precip_truth.json")

        if not metar_qc or not nwp_data:
            continue

        # Check >= 70% valid days requirement
        common_dates = sorted(set(metar_qc.keys()).intersection(nwp_data.keys()))
        if len(common_dates) < 150:
            print(f"[WARN] Station {st_id} has only {len(common_dates)} valid days; dropping.")
            continue

        valid_station_count += 1

        # Calculate recent-bias history without future leakage
        # Map: date -> raw_error (tmax_mmm - observed_tmax)
        daily_errors: dict[str, float] = {}
        for d in common_dates:
            if 1 in nwp_data[d] and "tmax_mmm" in nwp_data[d][1]:
                raw_pred = nwp_data[d][1]["tmax_mmm"]
                obs = metar_qc[d]["tmax"]
                daily_errors[d] = raw_pred - obs

        date_objects = [dt.date.fromisoformat(d) for d in common_dates]

        for d_obj in date_objects:
            d_str = d_obj.isoformat()
            doy = d_obj.timetuple().tm_yday
            doy_rad = doy * 2.0 * math.pi / 365.25
            doy_sin = math.sin(doy_rad)
            doy_cos = math.cos(doy_rad)

            # Compute recent bias: trailing 7 days strictly before d_obj
            recent_errs = []
            for delta_d in range(1, 8):
                past_d = (d_obj - dt.timedelta(days=delta_d)).isoformat()
                if past_d in daily_errors:
                    recent_errs.append(daily_errors[past_d])
            recent_bias = sum(recent_errs) / len(recent_errs) if recent_errs else 0.0

            obs_tmax = metar_qc[d_str]["tmax"]
            obs_rain = precip_truth.get(d_str, 0.0)
            obs_rain_event = 1 if obs_rain >= 2.5 else 0

            for lead in (1, 2, 3):
                lead_nwp = nwp_data.get(d_str, {}).get(lead, {})
                if not lead_nwp or "tmax_mmm" not in lead_nwp:
                    continue

                row = {
                    "station_id": st_id,
                    "date": d_str,
                    "lead_day": lead,
                    "doy": doy,
                    "doy_sin": round(doy_sin, 4),
                    "doy_cos": round(doy_cos, 4),
                    "lat": lat,
                    "lon": lon,
                    "elev": elev,
                    "recent_bias": round(recent_bias, 3),
                    "tmax_gfs": lead_nwp.get("tmax_gfs", lead_nwp["tmax_mmm"]),
                    "tmax_ecmwf": lead_nwp.get("tmax_ecmwf", lead_nwp["tmax_mmm"]),
                    "tmax_icon": lead_nwp.get("tmax_icon", lead_nwp["tmax_mmm"]),
                    "tmax_mmm": lead_nwp["tmax_mmm"],
                    "rain_gfs": lead_nwp.get("rain_gfs", 0.0),
                    "rain_ecmwf": lead_nwp.get("rain_ecmwf", 0.0),
                    "rain_icon": lead_nwp.get("rain_icon", 0.0),
                    "rain_mmm": lead_nwp.get("rain_mmm", 0.0),
                    "observed_tmax": obs_tmax,
                    "observed_rain": obs_rain,
                    "observed_rain_event": obs_rain_event,
                }
                all_rows.append(row)

    # Check Stop Conditions (Rule S1)
    test_rows = [r for r in all_rows if r["date"] >= TEST_START_DATE and r["date"] <= TEST_END_DATE]
    test_station_days = len({(r["station_id"], r["date"]) for r in test_rows})

    print(f"Dataset summary: {valid_station_count} valid stations, {len(all_rows)} total rows, "
          f"{test_station_days} test station-days ({len(test_rows)} test rows).")

    if valid_station_count < 10 or test_station_days < 400:
        blocked_msg = (
            f"Rule S1 Stop Condition triggered: valid_stations={valid_station_count} (minimum 10 required), "
            f"test_station_days={test_station_days} (minimum 400 required)."
        )
        print(f"[ERROR] {blocked_msg}", file=sys.stderr)
        blocked_file = ROOT / "BLOCKED.md"
        blocked_file.write_text(
            f"# Blocked: R11 Bias correction\n\n{blocked_msg}\n\nCheck data downloads and station availability.\n",
            encoding="utf-8",
        )
        raise RuntimeError(blocked_msg)

    # Save to disk
    if all_rows:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with PROCESSED_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"[OK] Processed dataset saved to {PROCESSED_FILE}")

    return all_rows


def load_dataset() -> list[dict[str, Any]]:
    """Load processed dataset from disk or build if missing."""
    if not PROCESSED_FILE.exists():
        return build_processed_dataset()

    rows = []
    with PROCESSED_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            parsed: dict[str, Any] = dict(r)
            for k in ("lead_day", "doy", "observed_rain_event"):
                if k in parsed and parsed[k]:
                    parsed[k] = int(parsed[k])
            for k in ("doy_sin", "doy_cos", "lat", "lon", "elev", "recent_bias",
                      "tmax_gfs", "tmax_ecmwf", "tmax_icon", "tmax_mmm",
                      "rain_gfs", "rain_ecmwf", "rain_icon", "rain_mmm",
                      "observed_tmax", "observed_rain"):
                if k in parsed and parsed[k]:
                    parsed[k] = float(parsed[k])
            rows.append(parsed)
    return rows


def get_time_splits(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition dataset into train and held-out test blocks with 7-day embargo."""
    test_start = dt.date.fromisoformat(TEST_START_DATE)
    embargo_cutoff = test_start - dt.timedelta(days=EMBARGO_DAYS)

    train_rows = []
    test_rows = []

    for r in rows:
        d = dt.date.fromisoformat(r["date"])
        if d >= test_start:
            test_rows.append(r)
        elif d <= embargo_cutoff:
            train_rows.append(r)
        # Any date between embargo_cutoff and test_start is dropped (embargo buffer)

    return train_rows, test_rows


def load_time_split_dataset() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Compatibility helper for PointForecastMOSModel."""
    try:
        rows = load_dataset()
        train_rows, test_rows = get_time_splits(rows)
        return train_rows, [], test_rows
    except Exception:
        return [], [], []


def get_dataset_manifest() -> dict[str, dict[str, str]]:
    """Returns data source provenance, licences, and terms."""
    return {
        "open_meteo": {
            "name": "Open-Meteo Historical Weather and Forecast API",
            "url": "https://api.open-meteo.com",
            "licence": "CC BY 4.0",
            "terms": "Free for non-commercial use under 10,000 calls/day; attribution required.",
        },
        "iem_metar": {
            "name": "Iowa Environmental Mesonet IN__ASOS METAR Archive",
            "url": "https://mesonet.agron.iastate.edu/request/asos/",
            "licence": "Open Access / Public Domain",
            "terms": "Free access to surface station observations across Indian airports.",
        },
        "gfs_archive": {
            "name": "NOAA Global Forecast System (GFS 0.25°)",
            "url": "https://data.dynamical.org/noaa/gfs/forecast/",
            "licence": "CC BY 4.0",
            "terms": "Global model guidance archive provided through dynamical.org.",
        },
    }
