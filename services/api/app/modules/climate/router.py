from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from services.api.app.modules.climate.service import ClimateService

router = APIRouter(prefix="/climate", tags=["climate"])
_service = ClimateService()


@router.get("")
async def get_climate(
    place_id: str = Query(..., description="Place identifier or name"),
    var: str = Query("temperature", description="Climate variable (temperature, rain)"),
    period: str = Query("2026-05", description="Period string (e.g. 2026-05 or 1991-2020)"),
    stat: str = Query("anomaly", description="Statistic (normal, anomaly, percentile, days_above_threshold, trend)"),
    threshold: float | None = Query(None, description="Optional threshold value for counts"),
    baseline: str = Query("1991-2020", description="Baseline normal period"),
) -> Any:
    return await _service.get_stat(
        place_id=place_id,
        variable=var,
        period=period,
        statistic=stat,
        threshold=threshold,
        baseline=baseline,
    )
