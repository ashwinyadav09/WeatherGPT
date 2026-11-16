from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from services.api.app.evidence.models import AlertModel
from services.api.app.modules.alerts.engine import AlertEngine

router = APIRouter(prefix="/alerts", tags=["alerts"])
_engine = AlertEngine()


@router.get("", response_model=list[AlertModel])
async def get_alerts(
    place_id: str | None = Query(None, description="Filter alerts by place"),
) -> Any:
    return await _engine.get_active_alerts(place_id=place_id)
