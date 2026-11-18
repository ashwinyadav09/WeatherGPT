from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from services.api.app.modules.aviation.decoder import calculate_wind_components
from services.api.app.modules.aviation.models import (
    AerodromeOverview,
    DecodedMetar,
    DecodedTaf,
    WindCalculation,
)
from services.api.app.modules.aviation.service import aviation_service

router = APIRouter(prefix="/aviation", tags=["aviation"])


@router.get("/metar", response_model=DecodedMetar)
async def get_metar(station: str = Query(..., min_length=4, max_length=4, description="4-letter ICAO station code")) -> DecodedMetar:
    """Returns decoded METAR alongside raw text, flight category, and mandatory non-briefing banner."""
    try:
        return await aviation_service.get_decoded_metar(station)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch METAR: {e}")


@router.get("/taf", response_model=DecodedTaf)
async def get_taf(station: str = Query(..., min_length=4, max_length=4, description="4-letter ICAO station code")) -> DecodedTaf:
    """Returns decoded TAF alongside raw text and mandatory non-briefing banner."""
    try:
        return await aviation_service.get_decoded_taf(station)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch TAF: {e}")


@router.get("/overview", response_model=AerodromeOverview)
async def get_overview(station: str = Query(..., min_length=4, max_length=4, description="4-letter ICAO station code")) -> AerodromeOverview:
    """Returns full aerodrome overview: decoded METAR, TAF, crosswind calculations across all runways, and recommendations."""
    try:
        return await aviation_service.get_aerodrome_overview(station)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to fetch overview: {e}")


@router.get("/crosswind", response_model=WindCalculation)
async def get_crosswind(
    runway_heading: int = Query(..., ge=0, le=360, description="Runway magnetic heading in degrees"),
    wind_dir: int = Query(..., ge=0, le=360, description="Wind direction in degrees"),
    wind_speed: float = Query(..., ge=0, description="Wind speed in knots"),
    wind_gust: float | None = Query(None, ge=0, description="Wind gust in knots"),
    runway_name: str = Query("RWY 09", description="Runway identifier label"),
) -> WindCalculation:
    """Computes exact crosswind, headwind/tailwind components, and crosswind component side."""
    return calculate_wind_components(
        runway_name=runway_name,
        runway_heading=runway_heading,
        wind_direction=wind_dir,
        wind_speed_kt=wind_speed,
        wind_gust_kt=wind_gust,
    )
