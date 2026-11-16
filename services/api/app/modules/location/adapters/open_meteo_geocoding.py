from __future__ import annotations

import httpx

from services.api.app.evidence.models import PlaceModel


class OpenMeteoGeocodingAdapter:
    def __init__(self, base_url: str = "https://geocoding-api.open-meteo.com/v1/search") -> None:
        self.base_url = base_url

    async def search(self, query: str, language: str = "en", count: int = 5) -> list[PlaceModel]:
        params: dict[str, str | int] = {"name": query, "count": count, "language": language}
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return []

        results: list[PlaceModel] = []
        for r in data.get("results", []):
            results.append(
                PlaceModel(
                    id=f"om_{r['id']}",
                    kind="district" if r.get("feature_code") == "ADM2" else "point",
                    names={language: r.get("name", query)},
                    lat=r["latitude"],
                    lon=r["longitude"],
                    elevation=r.get("elevation"),
                    state=r.get("admin1"),
                    district=r.get("admin2"),
                )
            )
        return results
