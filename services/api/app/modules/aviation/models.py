from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

FlightCategory = Literal["VFR", "MVFR", "IFR", "LIFR"]


class RunwayInfo(BaseModel):
    ident: str
    heading: int = Field(..., ge=0, le=360)
    reciprocal_heading: int = Field(..., ge=0, le=360)
    length_ft: int | None = None


class WindCalculation(BaseModel):
    runway: str
    runway_heading: int
    wind_direction: int
    wind_speed_kt: float
    wind_gust_kt: float | None = None
    relative_angle: int
    crosswind_kt: float
    crosswind_component_side: Literal["left", "right", "head", "tail", "calm"]
    headwind_kt: float
    is_tailwind: bool


class CloudLayer(BaseModel):
    cover: str  # SKC, FEW, SCT, BKN, OVC, NSC
    base_ft: int | None = None


class DecodedMetar(BaseModel):
    station: str
    raw: str
    observation_time_utc: dt.datetime
    observation_time_ist: str
    flight_category: FlightCategory
    wind_dir: int | None
    wind_speed_kt: float
    wind_gust_kt: float | None = None
    visibility_meters: int
    weather_conditions: list[str] = Field(default_factory=list)
    clouds: list[CloudLayer] = Field(default_factory=list)
    ceiling_ft: int | None = None
    temperature_c: float
    dewpoint_c: float
    qnh_hpa: float
    source: str = "AviationWeather.gov / NOAA"
    is_cached: bool = False
    fetched_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    banner: str = (
        "INFORMATIONAL ONLY: WeatherGPT aviation data is for situational awareness only and "
        "DOES NOT constitute an official pre-flight briefing. Pilots must obtain an official "
        "briefing from IMD / AAI / DGCA approved channels before flight."
    )


class TafPeriod(BaseModel):
    change_type: str | None = None  # BECMG, TEMPO, FM, PROB30, PROB40
    valid_from: dt.datetime
    valid_to: dt.datetime
    wind_dir: int | None = None
    wind_speed_kt: float | None = None
    visibility_meters: int | None = None
    weather_conditions: list[str] = Field(default_factory=list)
    clouds: list[CloudLayer] = Field(default_factory=list)


class DecodedTaf(BaseModel):
    station: str
    raw: str
    issue_time_utc: dt.datetime
    valid_from: dt.datetime
    valid_to: dt.datetime
    periods: list[TafPeriod] = Field(default_factory=list)
    summary: str
    source: str = "AviationWeather.gov / NOAA"
    is_cached: bool = False
    fetched_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    banner: str = (
        "INFORMATIONAL ONLY: WeatherGPT aviation data is for situational awareness only and "
        "DOES NOT constitute an official pre-flight briefing. Pilots must obtain an official "
        "briefing from IMD / AAI / DGCA approved channels before flight."
    )


class AerodromeOverview(BaseModel):
    station: str
    name: str
    metar: DecodedMetar | None = None
    taf: DecodedTaf | None = None
    runways: list[RunwayInfo] = Field(default_factory=list)
    wind_calculations: list[WindCalculation] = Field(default_factory=list)
    primary_runway_recommendation: str | None = None
    banner: str = (
        "INFORMATIONAL ONLY: WeatherGPT aviation data is for situational awareness only and "
        "DOES NOT constitute an official pre-flight briefing. Pilots must obtain an official "
        "briefing from IMD / AAI / DGCA approved channels before flight."
    )
