from __future__ import annotations

from services.api.app.evidence.models import PlaceModel
from services.api.app.modules.location.adapters.open_meteo_geocoding import OpenMeteoGeocodingAdapter

SEED_PLACES = [
    PlaceModel(
        id="pune",
        kind="district",
        names={"en": "Pune", "hi": "पुणे"},
        lat=18.5204,
        lon=73.8567,
        elevation=560.0,
        state="Maharashtra",
        district="Pune",
    ),
    PlaceModel(
        id="nagpur",
        kind="district",
        names={"en": "Nagpur", "hi": "नागपुर"},
        lat=21.1458,
        lon=79.0882,
        elevation=310.0,
        state="Maharashtra",
        district="Nagpur",
    ),
    PlaceModel(
        id="delhi",
        kind="district",
        names={"en": "Delhi", "hi": "दिल्ली"},
        lat=28.6139,
        lon=77.2090,
        elevation=216.0,
        state="Delhi",
        district="New Delhi",
    ),
]


class LocationResolver:
    def __init__(self, geocoder: OpenMeteoGeocodingAdapter | None = None) -> None:
        self.geocoder = geocoder or OpenMeteoGeocodingAdapter()

    async def search(self, query: str, language: str = "en") -> list[PlaceModel]:
        q_lower = query.lower().strip()
        matched = [
            p for p in SEED_PLACES
            if any(q_lower in name.lower() for name in p.names.values())
        ]
        if matched:
            return matched

        return await self.geocoder.search(query=query, language=language)

    async def resolve(self, text: str, language: str = "en", hint: str | None = None) -> dict[str, object]:
        places = await self.search(text, language)
        return {
            "places": places,
            "ambiguous": len(places) > 1,
        }

    async def get_by_id(self, place_id: str) -> PlaceModel | None:
        for p in SEED_PLACES:
            if p.id == place_id:
                return p
        return None
