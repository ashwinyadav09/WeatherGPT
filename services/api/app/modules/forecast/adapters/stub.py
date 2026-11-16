from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem
from services.api.app.modules.forecast.adapters.base import ForecastAdapter


class StubForecastAdapter(ForecastAdapter):
    @property
    def source_id(self) -> str:
        return "open_meteo.forecast"

    async def get_forecast(self, lat: float, lon: float, place_name: str, **kwargs: Any) -> list[EvidencePacket]:
        now = dt.datetime.now(dt.timezone.utc)
        return [
            EvidencePacket(
                id=str(uuid.uuid4()),
                source="open_meteo.forecast",
                authority_tier=5,
                provenance="documented-sample",
                issued_at=now,
                valid_from=now,
                valid_to=now + dt.timedelta(days=1),
                place=PlaceReference(
                    id=f"pt_{lat}_{lon}",
                    name=place_name,
                    lat=lat,
                    lon=lon,
                ),
                values=[
                    ValueItem(variable="temperature", value=28.5, unit="degC"),
                    ValueItem(variable="rain", value=0.0, unit="mm"),
                    ValueItem(variable="humidity", value=65.0, unit="%"),
                ],
                attribution="Weather data by Open-Meteo.com (CC BY 4.0)",
                fetched_at=now,
            )
        ]
