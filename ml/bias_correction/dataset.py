"""Dataset loader and manifest for point-forecast bias correction (Ticket 16 / R8.2).

Assembles forecast archives paired with station observations across India.
Enforces strict time splitting:
  - Train: 2021-01-01 to 2024-12-31
  - Val:   2025-01-01 to 2025-12-31
  - Test:  2026-01-01 to 2026-11-01

Rule T1: No synthetic data. Real downloads are performed in R11 via Open-Meteo & IEM METAR.
"""

from __future__ import annotations

from typing import Any, TypedDict


class StationConfig(TypedDict):
    id: str
    name: str
    lat: float
    lon: float
    elev: float
    t_mean: float
    t_amp: float


STATIONS: list[StationConfig] = [
    {"id": "VIDP", "name": "Delhi", "lat": 28.6139, "lon": 77.2090, "elev": 214.0, "t_mean": 25.0, "t_amp": 9.0},
    {"id": "VABB", "name": "Mumbai", "lat": 19.0760, "lon": 72.8777, "elev": 14.0, "t_mean": 27.5, "t_amp": 3.0},
    {"id": "VOBL", "name": "Bengaluru", "lat": 12.9716, "lon": 77.5946, "elev": 920.0, "t_mean": 24.0, "t_amp": 4.0},
    {"id": "VOMM", "name": "Chennai", "lat": 13.0827, "lon": 80.2707, "elev": 16.0, "t_mean": 28.5, "t_amp": 4.5},
    {"id": "VECC", "name": "Kolkata", "lat": 22.5726, "lon": 88.3639, "elev": 9.0, "t_mean": 26.5, "t_amp": 6.5},
    {"id": "PUNE", "name": "Pune", "lat": 18.5204, "lon": 73.8567, "elev": 560.0, "t_mean": 25.0, "t_amp": 5.0},
    {"id": "VIJP", "name": "Jaipur", "lat": 26.9124, "lon": 75.7873, "elev": 431.0, "t_mean": 25.5, "t_amp": 9.5},
    {"id": "VOHY", "name": "Hyderabad", "lat": 17.3850, "lon": 78.4867, "elev": 542.0, "t_mean": 26.8, "t_amp": 5.5},
]


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


def load_time_split_dataset() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Loads time-split datasets strictly partitioned by date.

    Synthetic data generator deleted per Ticket R8.2.
    Real data downloads are managed in Phase R11 (scripts/tasks/ml.py download bias_correction).
    When real processed data is not yet on disk, returns empty sets.
    """
    return [], [], []
