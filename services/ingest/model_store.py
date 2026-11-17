from __future__ import annotations

import datetime as dt
from typing import Any


class ModelOutputStore:
    """In-memory and file-backed store for ingested GFS and ECMWF model fields.

    Tracks model cycle, lead times, variables, and India bounding box (lat 6-38, lon 68-98).
    """

    def __init__(self) -> None:
        self._runs: dict[str, dict[str, Any]] = {}

    def record_cycle(
        self,
        model: str,
        cycle_time: dt.datetime,
        lead_hours: list[int],
        variables: list[str],
        grid_resolution_deg: float = 0.25,
        bounds: dict[str, float] | None = None,
    ) -> str:
        cycle_id = f"{model}:{cycle_time.strftime('%Y%m%d_%H%M')}"
        india_bounds = bounds or {"lat_min": 6.0, "lat_max": 38.0, "lon_min": 68.0, "lon_max": 98.0}

        self._runs[cycle_id] = {
            "model": model,
            "cycle_time": cycle_time.isoformat(),
            "lead_hours": lead_hours,
            "variables": variables,
            "grid_resolution_deg": grid_resolution_deg,
            "bounds": india_bounds,
            "ingested_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "ready",
        }
        return cycle_id

    def get_latest_cycle(self, model: str) -> dict[str, Any] | None:
        matching = [run for run in self._runs.values() if run["model"] == model]
        if not matching:
            return None
        matching.sort(key=lambda r: r["cycle_time"], reverse=True)
        return matching[0]

    def list_cycles(self) -> list[dict[str, Any]]:
        return list(self._runs.values())
