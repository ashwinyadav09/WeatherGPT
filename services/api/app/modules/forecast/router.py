from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from services.api.app.evidence.models import EvidencePacket
from services.api.app.modules.forecast.service import ForecastService

router = APIRouter(prefix="/forecast", tags=["forecast"])
_service = ForecastService()


@router.get("", response_model=list[EvidencePacket])
async def get_forecast(
    place_id: str = Query(..., description="Place ID"),
    window: str = Query("24h", description="Forecast window"),
) -> Any:
    return await _service.get_forecast(place_id=place_id, window=window)
