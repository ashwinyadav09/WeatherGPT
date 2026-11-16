from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from services.api.app.modules.advisory.engine import AdvisoryEngine

router = APIRouter(prefix="/advisory", tags=["advisory"])
_engine = AdvisoryEngine()


@router.get("")
async def get_advisories(
    place_id: str = Query(...),
    domain: str = Query("heat"),
    crop: str | None = Query(None),
) -> Any:
    return await _engine.get_advisory(place_id=place_id, domain=domain, crop=crop)
