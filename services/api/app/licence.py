from __future__ import annotations

from pydantic import BaseModel


class LicenceEntry(BaseModel):
    source_id: str
    name: str
    terms: str
    limits: str
    attribution_text: str


LICENCE_REGISTER: list[LicenceEntry] = [
    LicenceEntry(
        source_id="open_meteo.forecast",
        name="Open-Meteo Weather Forecast API",
        terms="CC BY 4.0, Non-commercial use",
        limits="Under 10,000 calls/day, 5,000/hour, 600/minute",
        attribution_text="Weather data by Open-Meteo.com (CC BY 4.0)",
    ),
    LicenceEntry(
        source_id="sachet.cap",
        name="NDMA SACHET Alert Feed",
        terms="National public safety disaster alert feeds, relay as issued",
        limits="Periodic polling under 60 requests/hour",
        attribution_text="National Disaster Management Authority (NDMA) SACHET",
    ),
    LicenceEntry(
        source_id="imd.city_forecast",
        name="India Meteorological Department (IMD)",
        terms="Government of India public data, non-commercial public interest",
        limits="Cached 15m; rate limit backed off gracefully",
        attribution_text="India Meteorological Department (IMD), Ministry of Earth Sciences",
    ),
    LicenceEntry(
        source_id="ecmwf.ifs",
        name="ECMWF Open Data",
        terms="CC-BY-4.0",
        limits="Open data policy",
        attribution_text="European Centre for Medium-Range Weather Forecasts (ECMWF)",
    ),
    LicenceEntry(
        source_id="aviationweather.gov",
        name="AviationWeather.gov (NOAA / NWS)",
        terms="Public domain US government data, non-briefing situational awareness",
        limits="Under 100 requests/minute and 1 request/minute per station endpoint",
        attribution_text="Aviation weather observations and forecasts by AviationWeather.gov / NOAA",
    ),
]


def get_licence_register() -> list[LicenceEntry]:
    return LICENCE_REGISTER
