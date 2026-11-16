from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from services.api.app.evidence.models import EvidencePacket


class ForecastAdapter(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str:
        ...

    @abstractmethod
    async def get_forecast(self, lat: float, lon: float, place_name: str, **kwargs: Any) -> list[EvidencePacket]:
        ...
