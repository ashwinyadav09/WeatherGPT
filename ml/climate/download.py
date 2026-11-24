"""Download and cache ERA5 reanalysis daily records from Open-Meteo Archive API (Ticket R13).

Fetches 1950 to 2024 daily maximum temperature, minimum temperature, and precipitation
for key Indian locations, snapped to 0.25° grid cells.
Stores cached JSON files in ml/climate/data/cache/ and records provenance in MANIFEST.json.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "ml" / "climate" / "data" / "cache"
MANIFEST_FILE = ROOT / "ml" / "climate" / "data" / "MANIFEST.json"
FIXTURES_DIR = ROOT / "eval" / "fixtures" / "climate"

# Grid cells for benchmark and event locations (lat_025, lon_025, label)
TARGET_CELLS: list[tuple[float, float, str]] = [
    (28.50, 77.25, "delhi"),
    (19.00, 73.00, "mumbai"),
    (18.50, 73.75, "pune"),
    (22.50, 88.25, "kolkata"),
    (13.00, 77.50, "bengaluru"),
    (13.00, 80.25, "chennai"),
    (27.00, 75.75, "jaipur"),
    (31.00, 77.25, "shimla"),
    (17.50, 78.50, "hyderabad"),
    (25.25, 83.00, "varanasi"),
    (10.00, 76.25, "kochi"),
    (30.25, 78.00, "dehradun"),
    (20.25, 85.75, "bhubaneswar"),
    (23.00, 72.50, "ahmedabad"),
]

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def snap_to_025(lat: float, lon: float) -> tuple[float, float]:
    """Snap latitude and longitude to 0.25 degree reanalysis grid."""
    return round(lat * 4) / 4, round(lon * 4) / 4


def cell_key(lat_025: float, lon_025: float) -> str:
    """Canonical string key for a 0.25 grid cell."""
    return f"{lat_025:.2f}_{lon_025:.2f}"


def fetch_cell_data(
    lat_025: float,
    lon_025: float,
    start_date: str = "1950-01-01",
    end_date: str = "2024-12-31",
    client: httpx.Client | None = None,
    max_retries: int = 5,
) -> dict[str, Any]:
    """Fetch daily ERA5 reanalysis series from Open-Meteo Archive API with rate-limit retry."""
    params: dict[str, Any] = {
        "latitude": lat_025,
        "longitude": lon_025,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "models": "era5",
        "timezone": "Asia/Kolkata",
    }
    c = client or httpx.Client(timeout=60.0)
    try:
        for attempt in range(max_retries):
            resp = c.get(ARCHIVE_URL, params=params)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                wait_sec = 65
                print(f"[RATE LIMIT] 429 received for {lat_025}_{lon_025}. Sleeping {wait_sec}s for minutely quota reset...")
                time.sleep(wait_sec)
                continue
            resp.raise_for_status()
        raise RuntimeError(f"Exceeded max retries fetching cell {lat_025}_{lon_025}")
    finally:
        if not client:
            c.close()


def download_all_target_cells(force: bool = False) -> None:
    """Download and persist real ERA5 records for all target cells."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[dict[str, Any]] = []

    with httpx.Client(timeout=30.0) as client:
        for lat, lon, label in TARGET_CELLS:
            ck = cell_key(lat, lon)
            cache_file = CACHE_DIR / f"{ck}.json"
            fixture_file = FIXTURES_DIR / f"{label}_{ck}.json"

            if cache_file.exists() and not force:
                print(f"[CACHE] {label} ({ck}) already exists.")
                data_bytes = cache_file.read_bytes()
            else:
                print(f"[FETCH] Downloading ERA5 1950-2024 for {label} ({ck})...")
                data = fetch_cell_data(lat, lon, client=client)
                data_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
                cache_file.write_bytes(data_bytes)
                fixture_file.write_bytes(data_bytes)
                # Respect rate limits between calls
                time.sleep(0.5)

            sha = hashlib.sha256(data_bytes).hexdigest()
            manifest_entries.append({
                "cell_key": ck,
                "label": label,
                "lat": lat,
                "lon": lon,
                "file": str(cache_file.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha,
                "bytes": len(data_bytes),
                "provenance": "recorded_real_http",
                "source": "Open-Meteo Archive API (ERA5 Reanalysis)",
                "source_url": ARCHIVE_URL,
                "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            })

    manifest = {
        "dataset": "ERA5 Reanalysis 1950-2024 (Open-Meteo Archive)",
        "provenance": "recorded_real_http",
        "grid_resolution_deg": 0.25,
        "n_cells": len(manifest_entries),
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": manifest_entries,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[DONE] Wrote MANIFEST.json with {len(manifest_entries)} cell records.")


if __name__ == "__main__":
    download_all_target_cells()
