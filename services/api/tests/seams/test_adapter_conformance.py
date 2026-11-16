from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from packages.contracts.validator import validate_schema
from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
FIXTURE_PATH = ROOT / "eval" / "fixtures" / "open_meteo" / "pune_forecast.json"


@pytest.mark.asyncio
async def test_open_meteo_adapter_conformance():
    assert FIXTURE_PATH.exists(), f"Fixture missing at {FIXTURE_PATH}"
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        fixture_data = json.load(f)

    assert fixture_data.get("_provenance") == "documented-sample"

    # Use a custom transport that returns the recorded fixture
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=fixture_data)

    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)

    adapter = OpenMeteoForecastAdapter(client=client)
    packets = await adapter.get_forecast(lat=18.52, lon=73.86, place_name="Pune")

    assert len(packets) == 1
    packet = packets[0]
    data = packet.model_dump(mode="json")

    # Strict conformance against Evidence Packet schema
    validate_schema("evidence_packet", data)
    assert data["source"] == "open_meteo.forecast"
    assert data["authority_tier"] == 5
    assert len(data["values"]) > 0
