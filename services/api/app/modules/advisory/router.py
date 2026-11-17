from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from services.api.app.modules.advisory.engine import AdvisoryEngine

router = APIRouter(prefix="/advisory", tags=["advisory"])
_engine = AdvisoryEngine()


@router.get("")
async def get_advisories(
    place_id: str = Query(...),
    domain: str = Query("heat_wave"),
    language: str = Query("en"),
    crop: str = Query("wheat"),
    stage: str = Query("sowing"),
) -> Any:
    return await _engine.get_advisory(
        place_id=place_id,
        domain=domain,
        language=language,
        crop=crop,
        stage=stage,
    )


@router.get("/agromet")
async def get_agromet_advisory(
    district: str = Query(...),
    crop: str = Query("wheat"),
    stage: str = Query("sowing"),
    language: str = Query("en"),
    query_text: str = Query(""),
) -> Any:
    """IMD Gramin Krishi Mausam Sewa (GKMS) district agromet advisory for wheat and rice."""
    return await _engine.agromet_adapter.get_agromet_advisory(
        district=district,
        crop=crop,
        stage=stage,
        language=language,
        query_text=query_text,
    )


@router.get("/marine")
async def get_marine_bulletin(
    area: str = Query("konkan_goa"),
    language: str = Query("en"),
) -> Any:
    """IMD / INCOIS coastal weather bulletin, sea condition, and fishermen warning."""
    return await _engine.marine_adapter.get_marine_bulletin(
        area=area,
        language=language,
    )
