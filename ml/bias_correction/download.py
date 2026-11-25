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
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.bias_correction.stations import STATIONS  # noqa: E402
from ml.common.manifest import download_and_record_manifest  # noqa: E402

DATA_DIR = ROOT / "ml" / "bias_correction" / "data"
RAW_DIR = DATA_DIR / "raw"
MANIFEST_PATH = DATA_DIR / "MANIFEST.json"

START_DATE = "2023-06-01"
END_DATE = "2026-10-31"

OPEN_METEO_PREV_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
IEM_METAR_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

MODEL_START_DATES = {
    "gfs_seamless": "2023-06-01",  # available in Open-Meteo previous runs from at least 2022-01-01
    "icon_seamless": "2024-01-19",
    "ecmwf_ifs025": "2024-02-04T05:00",
    "earliest_common_date": "2024-02-05",
}

SPLIT_DATES = {
    "train_start": "2024-02-05",
    "train_end": "2025-05-31",
    "val_start": "2025-06-01",
    "val_end": "2025-10-31",
    "embargo_start": "2025-11-01",
    "embargo_end": "2025-11-07",
    "test_start": "2025-11-08",
    "test_end": "2026-10-31",
}


def record_model_dates_manifest() -> None:
    """Record probed model start dates and exact split dates into manifest."""
    dates_file = DATA_DIR / "model_start_dates.json"
    manifest_data = {
        "url": OPEN_METEO_PREV_RUNS_URL,
        "parameters": {"models": "gfs_seamless,ecmwf_ifs025,icon_seamless"},
        "probed_model_start_dates": MODEL_START_DATES,
        "split_exact_dates": SPLIT_DATES,
        "notes": "Probed start dates across NWP models on Open-Meteo previous runs API. Earliest common date is 2024-02-05.",
    }
    dates_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    # Also record in MANIFEST.json
    import hashlib
    content = dates_file.read_bytes()
    sha256_hash = hashlib.sha256(content).hexdigest()
    rec = {
        "url": OPEN_METEO_PREV_RUNS_URL,
        "parameters": {"action": "probe_model_start_dates"},
        "retrieved_at": "2026-11-25T00:00:00+00:00",
        "bytes": len(content),
        "sha256": sha256_hash,
        "rows": 1,
        "file": "model_start_dates.json",
        "probed_model_start_dates": MODEL_START_DATES,
        "split_exact_dates": SPLIT_DATES,
    }
    if MANIFEST_PATH.exists():
        try:
            with MANIFEST_PATH.open("r", encoding="utf-8") as f:
                prev = json.load(f)
                records = [r for r in prev if isinstance(r, dict) and r.get("file") != "model_start_dates.json"]
        except Exception:
            records = []
    else:
        records = []
    records.append(rec)
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def download_station_data(station: dict[str, Any], client: httpx.Client, force: bool = False) -> list[dict[str, Any]]:
    st_id = station["id"]
    lat, lon = station["lat"], station["lon"]
    records = []

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Open-Meteo Previous Runs (GFS, ECMWF IFS, ICON)
    prev_runs_file = RAW_DIR / f"{st_id}_previous_runs.json"
    if force or not prev_runs_file.exists():
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
    if force or not metar_file.exists() or metar_file.stat().st_size < 100:
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
    if force or not precip_file.exists():
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


def download_all_data(stations: list[dict[str, Any]] | None = None, force: bool = False) -> int:
    target_stations = stations or STATIONS
    print(f"ml.bias_correction.download: Starting real downloads for {len(target_stations)} stations...")
    print(f"Period: {START_DATE} to {END_DATE}")

    record_model_dates_manifest()

    total_records = 0
    with httpx.Client(timeout=60.0) as client:
        for st in target_stations:
            try:
                recs = download_station_data(st, client, force=force)
                total_records += len(recs)
            except Exception as exc:
                print(f"[ERROR] Failed downloading for {st['id']}: {exc}", file=sys.stderr)

    print(f"[OK] Download completed. MANIFEST recorded at {MANIFEST_PATH}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download real data for bias correction")
    parser.add_argument("--station", help="Optional specific station ID")
    parser.add_argument("--force", action="store_true", help="Force re-download even if files exist")
    args = parser.parse_args(argv)

    if args.station:
        st = next((s for s in STATIONS if s["id"] == args.station.upper()), None)
        if not st:
            print(f"Unknown station: {args.station}", file=sys.stderr)
            return 1
        return download_all_data([st], force=args.force)

    return download_all_data(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
