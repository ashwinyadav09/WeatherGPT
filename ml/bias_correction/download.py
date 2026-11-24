"""Download real NWP forecasts and METAR observations for bias correction (Ticket R11).

Downloads:
1. Open-Meteo Previous Runs API:
   - Models: gfs_seamless, ecmwf_ifs025, icon_seamless
   - Variables: temperature_2m_previous_day1..3, precipitation_previous_day1..3
2. IEM ASOS METAR Archive:
   - Hourly station temperature observations in IST
3. Open-Meteo Archive API:
   - Daily precipitation_sum as precipitation truth proxy

Strictly writes MANIFEST.json per source (Rule T1, T6, T7).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import httpx

from ml.bias_correction.stations import STATIONS
from ml.common.manifest import download_and_record_manifest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA_DIR = ROOT / "ml" / "bias_correction" / "data"
RAW_DIR = DATA_DIR / "raw"
MANIFEST_PATH = DATA_DIR / "MANIFEST.json"

START_DATE = "2023-06-01"
END_DATE = "2024-10-31"

OPEN_METEO_PREV_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
IEM_METAR_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"


def download_station_data(station: dict[str, Any], client: httpx.Client) -> list[dict[str, Any]]:
    st_id = station["id"]
    lat, lon = station["lat"], station["lon"]
    records = []

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Open-Meteo Previous Runs (GFS, ECMWF IFS, ICON)
    prev_runs_file = RAW_DIR / f"{st_id}_previous_runs.json"
    if not prev_runs_file.exists():
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "hourly": (
                "temperature_2m_previous_day1,temperature_2m_previous_day2,temperature_2m_previous_day3,"
                "precipitation_previous_day1,precipitation_previous_day2,precipitation_previous_day3"
            ),
            "models": "gfs_seamless,ecmwf_ifs025,icon_seamless",
            "timezone": "Asia/Kolkata",
        }
        print(f"[{st_id}] Downloading NWP previous runs (GFS, ECMWF, ICON)...")
        rec = download_and_record_manifest(
            url=OPEN_METEO_PREV_RUNS_URL,
            output_path=prev_runs_file,
            params=params,
            manifest_path=MANIFEST_PATH,
            client=client,
            timeout=45.0,
        )
        records.append(rec)
        time.sleep(0.5)

    # 2. IEM METAR Observations
    metar_file = RAW_DIR / f"{st_id}_metar.csv"
    if not metar_file.exists() or metar_file.stat().st_size < 100:
        # IEM date parameters: year1, month1, day1, year2, month2, day2
        s_parts = START_DATE.split("-")
        e_parts = END_DATE.split("-")
        params = {
            "station": st_id,
            "data": "tmpc",
            "year1": int(s_parts[0]),
            "month1": int(s_parts[1]),
            "day1": int(s_parts[2]),
            "year2": int(e_parts[0]),
            "month2": int(e_parts[1]),
            "day2": int(e_parts[2]),
            "tz": "Asia/Kolkata",
            "format": "onlycomma",
            "latlon": "no",
            "missing": "M",
            "trace": "T",
            "direct": "no",
            "report_type": ["1", "2"],
        }
        print(f"[{st_id}] Downloading IEM METAR observations...")
        rec = download_and_record_manifest(
            url=IEM_METAR_URL,
            output_path=metar_file,
            params=params,
            manifest_path=MANIFEST_PATH,
            client=client,
            timeout=45.0,
        )
        records.append(rec)
        time.sleep(0.5)

    # 3. Open-Meteo Archive daily precipitation (proxy truth for rain)
    precip_file = RAW_DIR / f"{st_id}_precip_truth.json"
    if not precip_file.exists():
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "daily": "precipitation_sum",
            "timezone": "Asia/Kolkata",
        }
        print(f"[{st_id}] Downloading Open-Meteo archive precipitation proxy...")
        rec = download_and_record_manifest(
            url=OPEN_METEO_ARCHIVE_URL,
            output_path=precip_file,
            params=params,
            manifest_path=MANIFEST_PATH,
            client=client,
            timeout=45.0,
        )
        records.append(rec)
        time.sleep(0.5)

    return records


def download_all_data(stations: list[dict[str, Any]] | None = None) -> int:
    target_stations = stations or STATIONS
    print(f"ml.bias_correction.download: Starting real downloads for {len(target_stations)} stations...")
    print(f"Period: {START_DATE} to {END_DATE}")

    total_records = 0
    with httpx.Client(timeout=60.0) as client:
        for st in target_stations:
            try:
                recs = download_station_data(st, client)
                total_records += len(recs)
            except Exception as exc:
                print(f"[ERROR] Failed downloading for {st['id']}: {exc}", file=sys.stderr)

    print(f"[OK] Download completed. MANIFEST recorded at {MANIFEST_PATH}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download real data for bias correction")
    parser.add_argument("--station", help="Optional specific station ID")
    args = parser.parse_args(argv)

    if args.station:
        st = next((s for s in STATIONS if s["id"] == args.station.upper()), None)
        if not st:
            print(f"Unknown station: {args.station}", file=sys.stderr)
            return 1
        return download_all_data([st])

    return download_all_data()


if __name__ == "__main__":
    sys.exit(main())
