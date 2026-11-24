from __future__ import annotations

from typing import Any

from services.api.app.evidence.models import EvidencePacket
from services.api.app.modules.forecast.adapters.base import ForecastAdapter
from services.api.app.registry import FailoverForecastProvider, registry


class ForecastService:
    def __init__(self, provider: ForecastAdapter | None = None) -> None:
        self.adapters: dict[str, ForecastAdapter] = {}
        if provider:
            self.provider = provider
            self.adapters[getattr(provider, "source_id", "custom")] = provider
        else:
            available = registry.get_available_forecast_providers()
            for p in available:
                self.adapters[getattr(p, "source_id", type(p).__name__)] = p
            self.provider = FailoverForecastProvider(available)

    def register_adapter(self, adapter: ForecastAdapter) -> None:
        self.adapters[adapter.source_id] = adapter
        # Re-wrap provider with the newly registered adapter as primary
        other_adapters = [p for s_id, p in self.adapters.items() if s_id != adapter.source_id]
        self.provider = FailoverForecastProvider([adapter] + other_adapters)

    async def get_forecast(
        self,
        place_id: str = "pune",
        lat: float = 18.5204,
        lon: float = 73.8567,
        place_name: str = "Pune",
        ml_mode: str = "raw",
        elevation: float = 0.0,
        **kwargs: Any,
    ) -> list[EvidencePacket]:
        packets = await self.provider.get_forecast(
            lat=lat, lon=lon, place_name=place_name, place_id=place_id, **kwargs
        )
        if ml_mode == "ml":
            try:
                from ml.bias_correction.service import apply_bias_correction_hook
                return apply_bias_correction_hook(
                    packets=packets,
                    lat=lat,
                    lon=lon,
                    elev=elevation,
                    ml_mode=ml_mode,
                )
            except Exception:
                return packets
        return packets
