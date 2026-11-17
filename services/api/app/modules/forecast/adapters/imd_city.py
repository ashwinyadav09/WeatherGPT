from __future__ import annotations

import datetime as dt
import json
import os
import uuid
from pathlib import Path
from typing import Any, Literal

import httpx

from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem
from services.api.app.modules.forecast.adapters.base import ForecastAdapter

ROOT = Path(__file__).resolve().parents[6]
SAMPLE_FIXTURE = ROOT / "eval" / "fixtures" / "imd" / "city_forecast_sample.json"


class IMDCityForecastAdapter(ForecastAdapter):
    def __init__(self, base_url: str = "https://api.imd.gov.in", client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url
        self._client = client

    @property
    def source_id(self) -> str:
        return "imd.city_forecast"

    async def get_forecast(self, lat: float, lon: float, place_name: str, **kwargs: Any) -> list[EvidencePacket]:
        api_key = os.getenv("IMD_API_KEY")
        data: dict[str, Any] = {}

        # If live API key is not available or call fails, use documented sample (ADR 0007)
        if not api_key:
            if SAMPLE_FIXTURE.exists():
                with SAMPLE_FIXTURE.open("r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                raise FileNotFoundError(f"IMD documented sample fixture not found at {SAMPLE_FIXTURE}")
        else:
            client = self._client or httpx.AsyncClient(timeout=10.0)
            try:
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = await client.get(f"{self.base_url}/city_forecast", headers=headers, params={"lat": lat, "lon": lon})
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                if SAMPLE_FIXTURE.exists():
                    with SAMPLE_FIXTURE.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    raise
            finally:
                if not self._client:
                    await client.aclose()

        now = dt.datetime.now(dt.timezone.utc)
        provenance: Literal["live", "live-recorded", "documented-sample", "spec-only", "synthetic"] = (
            "live" if api_key and "Forecast" in data else "documented-sample"
        )
        forecast_items = data.get("Forecast", [])

        values: list[ValueItem] = []
        valid_to = now + dt.timedelta(days=1)

        for item in forecast_items:
            date_str = item.get("Date", "")
            if "Max_Temp" in item:
                try:
                    values.append(ValueItem(variable="max_temperature", value=float(item["Max_Temp"]), unit="degC", step=date_str))
                except ValueError:
                    pass
            if "Min_Temp" in item:
                try:
                    values.append(ValueItem(variable="min_temperature", value=float(item["Min_Temp"]), unit="degC", step=date_str))
                except ValueError:
                    pass
            if "Rainfall_mm" in item:
                try:
                    values.append(ValueItem(variable="rain", value=float(item["Rainfall_mm"]), unit="mm", step=date_str))
                except ValueError:
                    pass
            if "Weather_Desc" in item:
                values.append(ValueItem(variable="weather_condition", value=item["Weather_Desc"], unit="text", step=date_str))

        if forecast_items:
            valid_to = now + dt.timedelta(days=len(forecast_items))

        return [
            EvidencePacket(
                id=str(uuid.uuid4()),
                source="imd.city_forecast",
                authority_tier=2,
                provenance=provenance,
                issued_at=now,
                valid_from=now,
                valid_to=valid_to,
                place=PlaceReference(
                    id=f"pt_{lat}_{lon}",
                    name=place_name,
                    lat=lat,
                    lon=lon,
                ),
                values=values,
                attribution="India Meteorological Department (IMD), Ministry of Earth Sciences",
                fetched_at=now,
            )
        ]
