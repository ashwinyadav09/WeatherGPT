from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from services.api.app.modules.climate.service import ClimateService

router = APIRouter(prefix="/climate", tags=["climate"])
_service = ClimateService()


@router.get("")
async def get_climate(
    place_id: str = Query(...),
    var: str = Query("temperature"),
    period: str = Query("2026-05"),
    stat: str = Query("anomaly"),
) -> Any:
    return await _service.get_stat(place_id=place_id, variable=var, period=period, statistic=stat)
