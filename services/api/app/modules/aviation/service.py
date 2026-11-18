from __future__ import annotations

import datetime as dt
from typing import Any

from services.api.app.modules.aviation.adapter import AviationWeatherAdapter
from services.api.app.modules.aviation.decoder import (
    calculate_wind_components,
    decode_metar_raw,
)
from services.api.app.modules.aviation.models import (
    AerodromeOverview,
    DecodedMetar,
    DecodedTaf,
    RunwayInfo,
    WindCalculation,
)

AERODROMES: dict[str, dict[str, Any]] = {
    "VIDP": {
        "name": "Indira Gandhi International Airport, Delhi",
        "city": "Delhi",
        "runways": [
            RunwayInfo(ident="09/27", heading=90, reciprocal_heading=270, length_ft=9229),
            RunwayInfo(ident="10/28", heading=100, reciprocal_heading=280, length_ft=12500),
            RunwayInfo(ident="11/29", heading=110, reciprocal_heading=290, length_ft=14534),
        ],
    },
    "VABB": {
        "name": "Chhatrapati Shivaji Maharaj International Airport, Mumbai",
        "city": "Mumbai",
        "runways": [
            RunwayInfo(ident="09/27", heading=90, reciprocal_heading=270, length_ft=11302),
            RunwayInfo(ident="14/32", heading=140, reciprocal_heading=320, length_ft=9744),
        ],
    },
    "VOBL": {
        "name": "Kempegowda International Airport, Bengaluru",
        "city": "Bengaluru",
        "runways": [
            RunwayInfo(ident="09L/27R", heading=92, reciprocal_heading=272, length_ft=13123),
            RunwayInfo(ident="09R/27L", heading=92, reciprocal_heading=272, length_ft=13123),
        ],
    },
    "VOMM": {
        "name": "Chennai International Airport, Chennai",
        "city": "Chennai",
        "runways": [
            RunwayInfo(ident="07/25", heading=70, reciprocal_heading=250, length_ft=12000),
            RunwayInfo(ident="12/30", heading=120, reciprocal_heading=300, length_ft=6700),
        ],
    },
    "VECC": {
        "name": "Netaji Subhash Chandra Bose International Airport, Kolkata",
        "city": "Kolkata",
        "runways": [
            RunwayInfo(ident="01L/19R", heading=15, reciprocal_heading=195, length_ft=11900),
            RunwayInfo(ident="01R/19L", heading=15, reciprocal_heading=195, length_ft=9240),
        ],
    },
}


class AviationService:
    def __init__(self, adapter: AviationWeatherAdapter | None = None) -> None:
        self.adapter = adapter or AviationWeatherAdapter()

    async def get_decoded_metar(self, station: str) -> DecodedMetar:
        station = station.strip().upper()
        metar_data = await self.adapter.get_metar(station)
        raw_text = metar_data["raw"]

        decoded_fields = decode_metar_raw(raw_text)

        # Parse observation time
        time_str = metar_data.get("time_utc")
        if time_str:
            try:
                obs_utc = dt.datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except Exception:
                obs_utc = dt.datetime.now(dt.timezone.utc)
        else:
            obs_utc = dt.datetime.now(dt.timezone.utc)

        # Convert to IST display
        ist_offset = dt.timezone(dt.timedelta(hours=5, minutes=30))
        obs_ist = obs_utc.astimezone(ist_offset).strftime("%Y-%m-%d %H:%M IST")

        return DecodedMetar(
            station=station,
            raw=raw_text,
            observation_time_utc=obs_utc,
            observation_time_ist=obs_ist,
            flight_category=decoded_fields["flight_category"],
            wind_dir=decoded_fields["wind_dir"],
            wind_speed_kt=decoded_fields["wind_speed_kt"],
            wind_gust_kt=decoded_fields["wind_gust_kt"],
            visibility_meters=decoded_fields["visibility_meters"],
            weather_conditions=decoded_fields["weather_conditions"],
            clouds=decoded_fields["clouds"],
            ceiling_ft=decoded_fields["ceiling_ft"],
            temperature_c=decoded_fields["temperature_c"],
            dewpoint_c=decoded_fields["dewpoint_c"],
            qnh_hpa=decoded_fields["qnh_hpa"],
            source=metar_data.get("source", "AviationWeather.gov / NOAA"),
            is_cached=metar_data.get("is_cached", False),
        )

    async def get_decoded_taf(self, station: str) -> DecodedTaf:
        station = station.strip().upper()
        taf_data = await self.adapter.get_taf(station)

        raw_taf = taf_data["raw"]
        now = dt.datetime.now(dt.timezone.utc)

        return DecodedTaf(
            station=station,
            raw=raw_taf,
            issue_time_utc=now,
            valid_from=now,
            valid_to=now + dt.timedelta(hours=24),
            summary=taf_data.get("forecast_summary", "Terminal Aerodrome Forecast (TAF) issued."),
            source=taf_data.get("source", "AviationWeather.gov / NOAA"),
            is_cached=taf_data.get("is_cached", False),
        )

    async def get_aerodrome_overview(self, station: str) -> AerodromeOverview:
        station = station.strip().upper()
        meta = AERODROMES.get(station, {
            "name": f"Aerodrome {station}",
            "city": station,
            "runways": [RunwayInfo(ident="09/27", heading=90, reciprocal_heading=270, length_ft=10000)],
        })

        metar = await self.get_decoded_metar(station)
        taf = await self.get_decoded_taf(station)

        runways: list[RunwayInfo] = meta.get("runways", [])
        wind_calculations: list[WindCalculation] = []

        w_dir = metar.wind_dir
        w_spd = metar.wind_speed_kt
        w_gst = metar.wind_gust_kt

        best_runway: str | None = None
        min_crosswind = float("inf")

        for rwy in runways:
            parts = rwy.ident.split("/")
            # Check primary heading
            calc1 = calculate_wind_components(
                runway_name=f"RWY {parts[0]}",
                runway_heading=rwy.heading,
                wind_direction=w_dir,
                wind_speed_kt=w_spd,
                wind_gust_kt=w_gst,
            )
            wind_calculations.append(calc1)

            # Check reciprocal heading
            recip_ident = parts[1] if len(parts) > 1 else str((rwy.heading + 180) % 360 // 10)
            calc2 = calculate_wind_components(
                runway_name=f"RWY {recip_ident}",
                runway_heading=rwy.reciprocal_heading,
                wind_direction=w_dir,
                wind_speed_kt=w_spd,
                wind_gust_kt=w_gst,
            )
            wind_calculations.append(calc2)

            for c in (calc1, calc2):
                # Prefer headwind runways with lowest crosswind
                score = c.crosswind_kt + (5.0 if c.is_tailwind else 0.0)
                if score < min_crosswind:
                    min_crosswind = score
                    best_runway = c.runway

        return AerodromeOverview(
            station=station,
            name=meta["name"],
            metar=metar,
            taf=taf,
            runways=runways,
            wind_calculations=wind_calculations,
            primary_runway_recommendation=best_runway,
        )


aviation_service = AviationService()
