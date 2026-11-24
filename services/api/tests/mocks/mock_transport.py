"""Mock transports for unit tests under services/api/tests/ (Rule N1).

Provides canned/fixture HTTP transports for isolated unit testing only.
Never used in eval/**, ml/**, or production runtime code.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
FIXTURES_DIR = ROOT / "eval" / "fixtures" / "open_meteo"


def get_mock_forecast_transport() -> httpx.MockTransport:
    """MockTransport for unit tests routing queries to local test fixtures."""
    city_forecasts: dict[str, tuple[float, float, dict[str, Any]]] = {}
    if FIXTURES_DIR.exists():
        for f in FIXTURES_DIR.glob("*_forecast.json"):
            city = f.stem.replace("_forecast", "")
            if city == "differing_days":
                continue
            with f.open("r", encoding="utf-8") as jf:
                data = json.load(jf)
            city_forecasts[city] = (data.get("latitude", 0.0), data.get("longitude", 0.0), data)

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "forecast" in url_str:
            lat = float(request.url.params.get("latitude", 0.0))
            lon = float(request.url.params.get("longitude", 0.0))
            best_dist, best_data = float("inf"), None
            for _, (clat, clon, data) in city_forecasts.items():
                dist = ((lat - clat) ** 2 + (lon - clon) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_data = data
            if best_data is not None:
                return httpx.Response(200, json=best_data)
            return httpx.Response(200, json={})

        if "search" in url_str or "geocoding" in url_str:
            q_name = (request.url.params.get("name", "")).lower()
            geo_file = FIXTURES_DIR / f"{q_name}_geocoding.json"
            if geo_file.exists():
                with geo_file.open("r", encoding="utf-8") as gf:
                    return httpx.Response(200, json=json.load(gf))
            from services.api.app.modules.location.resolver import INDIA_PLACES
            matched_results = []
            for p in INDIA_PLACES:
                for n in p.names.values():
                    if q_name in n.lower() or n.lower() in q_name:
                        matched_results.append({
                            "id": p.id,
                            "name": p.names.get("en", p.id),
                            "latitude": p.lat,
                            "longitude": p.lon,
                            "country_code": "IN",
                            "admin1": p.state or "",
                        })
                        break
            return httpx.Response(200, json={"results": matched_results})

        return httpx.Response(200, json={})

    return httpx.MockTransport(handler)
