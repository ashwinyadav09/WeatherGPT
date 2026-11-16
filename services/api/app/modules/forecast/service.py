from __future__ import annotations

from typing import Any

from services.api.app.config import settings
from services.api.app.evidence.models import EvidencePacket
from services.api.app.modules.forecast.adapters.base import ForecastAdapter
from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
from services.api.app.modules.forecast.adapters.stub import StubForecastAdapter


class ForecastService:
    def __init__(self) -> None:
        self.adapters: dict[str, ForecastAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        # Register adapters based on settings / sources.yaml
        for src in settings.sources:
            if src.id == "open_meteo.forecast" and src.enabled:
                self.adapters[src.id] = OpenMeteoForecastAdapter(base_url=src.base_url)
        # Always have stub adapter available as fallback
        self.adapters["stub.forecast"] = StubForecastAdapter()

    def register_adapter(self, adapter: ForecastAdapter) -> None:
        self.adapters[adapter.source_id] = adapter

    async def get_forecast(
        self,
        place_id: str,
        lat: float = 18.5204,
        lon: float = 73.8567,
        place_name: str = "Pune",
        **kwargs: Any,
    ) -> list[EvidencePacket]:
        primary = "open_meteo.forecast" if "open_meteo.forecast" in self.adapters else "stub.forecast"
        adapter = self.adapters.get(primary, self.adapters["stub.forecast"])
        try:
            return await adapter.get_forecast(lat=lat, lon=lon, place_name=place_name, **kwargs)
        except Exception:
            return await self.adapters["stub.forecast"].get_forecast(lat=lat, lon=lon, place_name=place_name, **kwargs)
