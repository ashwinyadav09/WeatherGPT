from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal

import httpx

from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem
from services.api.app.modules.forecast.adapters.base import ForecastAdapter


class OpenMeteoForecastAdapter(ForecastAdapter):
    def __init__(self, base_url: str = "https://api.open-meteo.com/v1/forecast", client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url
        self._client = client

    @property
    def source_id(self) -> str:
        return "open_meteo.forecast"

    async def get_forecast(self, lat: float, lon: float, place_name: str, **kwargs: Any) -> list[EvidencePacket]:
        params: dict[str, str | int | float] = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
            "timezone": "Asia/Kolkata",
            "forecast_days": 7,
        }
        client = self._client or httpx.AsyncClient(timeout=5.0)
        try:
            resp = await client.get(self.base_url, params=params)
            resp.raise_for_status()
            data = resp.json()
        finally:
            if not self._client:
                await client.aclose()

        now = dt.datetime.now(dt.timezone.utc)
        provenance: Literal["live", "live-recorded", "documented-sample", "spec-only", "synthetic"] = (
            "live" if "current" in data and not getattr(self._client, "_is_fixture", False) else "documented-sample"
        )
        place_ref = PlaceReference(
            id=f"pt_{lat}_{lon}",
            name=place_name,
            lat=lat,
            lon=lon,
        )

        packets: list[EvidencePacket] = []

        # 1. Current conditions packet
        if "current" in data:
            curr = data["current"]
            current_values: list[ValueItem] = []
            if "temperature_2m" in curr and curr["temperature_2m"] is not None:
                current_values.append(ValueItem(variable="temperature", value=float(curr["temperature_2m"]), unit="degC"))
            if "precipitation" in curr and curr["precipitation"] is not None:
                current_values.append(ValueItem(variable="rain", value=float(curr["precipitation"]), unit="mm"))

            if current_values:
                packets.append(
                    EvidencePacket(
                        id=str(uuid.uuid4()),
                        source="open_meteo.forecast",
                        authority_tier=5,
                        provenance=provenance,
                        issued_at=now,
                        valid_from=now,
                        valid_to=now + dt.timedelta(hours=1),
                        place=place_ref,
                        values=current_values,
                        attribution="Weather data by Open-Meteo.com (CC BY 4.0)",
                        fetched_at=now,
                    )
                )

        # 2. 7-day daily forecast packets (each with its own valid_from and valid_to)
        if "daily" in data:
            daily = data["daily"]
            times = daily.get("time", [])
            tmax_list = daily.get("temperature_2m_max", [])
            tmin_list = daily.get("temperature_2m_min", [])
            rain_sum_list = daily.get("precipitation_sum", [])
            rain_prob_list = daily.get("precipitation_probability_max", [])

            n_days = len(times)
            for i in range(n_days):
                date_str = times[i]
                try:
                    day_start = dt.datetime.fromisoformat(f"{date_str}T00:00:00+05:30")
                except Exception:
                    day_start = now + dt.timedelta(days=i)
                day_end = day_start + dt.timedelta(days=1)

                day_values: list[ValueItem] = []
                if i < len(tmax_list) and tmax_list[i] is not None:
                    day_values.append(ValueItem(variable="tmax", value=float(tmax_list[i]), unit="degC", step=i))
                if i < len(tmin_list) and tmin_list[i] is not None:
                    day_values.append(ValueItem(variable="tmin", value=float(tmin_list[i]), unit="degC", step=i))
                if i < len(rain_sum_list) and rain_sum_list[i] is not None:
                    day_values.append(ValueItem(variable="rain_sum", value=float(rain_sum_list[i]), unit="mm", step=i))
                if i < len(rain_prob_list) and rain_prob_list[i] is not None:
                    day_values.append(ValueItem(variable="rain_probability_max", value=float(rain_prob_list[i]), unit="%", step=i))

                if day_values:
                    packets.append(
                        EvidencePacket(
                            id=str(uuid.uuid4()),
                            source="open_meteo.forecast",
                            authority_tier=5,
                            provenance=provenance,
                            issued_at=now,
                            valid_from=day_start,
                            valid_to=day_end,
                            place=place_ref,
                            values=day_values,
                            attribution="Weather data by Open-Meteo.com (CC BY 4.0)",
                            fetched_at=now,
                        )
                    )

        return packets
