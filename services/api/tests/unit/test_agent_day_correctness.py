"""Unit tests for agent correctness, day indexing, and missing data handling (Ticket R0.3).

Requirements:
- OpenMeteoForecastAdapter emits current conditions + per-day values for all 7 days
  (tmax, tmin, rain_sum, rain_probability_max), each with its own valid_from and valid_to.
- Questions about "tomorrow" use day index 1.
- No defaults: 28.5 °C, 0.0 mm, and "Pune" defaults are removed.
  Missing place -> asks user for clarification.
  Missing values -> reports data unavailable.
- Verifier rejects any number not in evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from services.api.app.agent.orchestrator import ChatRequest, Orchestrator
from services.api.app.conversation.verifier import verify_grounding
from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem
from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
from services.api.app.modules.forecast.service import ForecastService

ROOT = Path(__file__).resolve().parents[4]
DIFFERING_FIXTURE = ROOT / "eval" / "fixtures" / "open_meteo" / "differing_days_forecast.json"


@pytest.fixture
def mock_open_meteo_client():
    with DIFFERING_FIXTURE.open("r", encoding="utf-8") as f:
        fixture_data = json.load(f)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=fixture_data)

    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport)


@pytest.mark.asyncio
async def test_open_meteo_adapter_emits_all_7_days_and_current(mock_open_meteo_client):
    """Adapter must emit 1 current conditions packet + 7 daily packets with own valid_from/to."""
    adapter = OpenMeteoForecastAdapter(client=mock_open_meteo_client)
    packets = await adapter.get_forecast(lat=18.52, lon=73.86, place_name="Pune")

    # 1 current conditions + 7 daily forecast packets = 8 packets
    assert len(packets) == 8, f"Expected 8 packets (1 current + 7 daily), got {len(packets)}"

    current_pkt = packets[0]
    assert current_pkt.values[0].variable == "temperature"

    daily_pkts = packets[1:]
    assert len(daily_pkts) == 7

    # Check Day 0 (today)
    day0 = daily_pkts[0]
    day0_vars = {v.variable: v.value for v in day0.values}
    assert day0_vars["tmax"] == 35.0
    assert day0_vars["tmin"] == 24.0
    assert day0_vars["rain_sum"] == 0.0
    assert day0_vars["rain_probability_max"] == 5

    # Check Day 1 (tomorrow)
    day1 = daily_pkts[1]
    day1_vars = {v.variable: v.value for v in day1.values}
    assert day1_vars["tmax"] == 22.0
    assert day1_vars["tmin"] == 15.0
    assert day1_vars["rain_sum"] == 18.5
    assert day1_vars["rain_probability_max"] == 90

    # Ensure each day has distinct valid_from and valid_to
    for i in range(len(daily_pkts) - 1):
        assert daily_pkts[i].valid_from < daily_pkts[i + 1].valid_from
        assert daily_pkts[i].valid_to <= daily_pkts[i + 1].valid_from


@pytest.mark.asyncio
async def test_agent_tomorrow_uses_day_index_1(mock_open_meteo_client):
    """'Will it rain tomorrow in Pune?' must report Day 1 values (18.5 mm, 22.0 °C), not Day 0 (0.0 mm, 35.0 °C)."""
    adapter = OpenMeteoForecastAdapter(client=mock_open_meteo_client)
    forecast_service = ForecastService()
    forecast_service.register_adapter(adapter)

    agent = Orchestrator(forecast_service=forecast_service)
    req = ChatRequest(
        session_id="test_tomorrow_day1",
        text="Will it rain tomorrow in Pune?",
        language="en",
        stream=True,
    )

    tokens = []
    card_data = None
    evidence_packets = []
    async for event in agent.run_chat(req):
        if event["event"] == "token":
            tokens.append(event["data"]["text"])
        elif event["event"] == "card":
            card_data = event["data"]
        elif event["event"] == "evidence":
            evidence_packets.append(EvidencePacket.model_validate(event["data"]))

    answer_text = "".join(tokens)

    # Must contain tomorrow's values: 18.5 mm and 22.0 degC
    assert "18.5" in answer_text, f"Expected tomorrow's rain (18.5 mm) in answer: {answer_text}"
    assert "22.0" in answer_text, f"Expected tomorrow's temperature (22.0 degC) in answer: {answer_text}"

    # Must NOT contain today's tmax (35.0) or current temp (29.0) as tomorrow's forecast
    assert "35.0" not in answer_text, "Answer incorrectly used today's tmax for tomorrow"

    # Card key_values must also reflect Day 1
    assert card_data is not None
    assert "18.5 mm" in card_data["key_values"].get("Rain", "")
    assert "22.0 degC" in card_data["key_values"].get("Temperature", "")

    # Grounding verifier must confirm all numbers are grounded in evidence
    v_res = verify_grounding(answer_text, evidence_packets)
    assert v_res.is_grounded, f"Verifier rejected answer: {v_res.reasons}"


@pytest.mark.asyncio
async def test_agent_missing_place_asks_clarification():
    """Asking without place and without place_id must NOT default to Pune; must ask user for place."""
    agent = Orchestrator()
    req = ChatRequest(
        session_id="test_no_place",
        text="Will it rain tomorrow?",  # No place mentioned
        language="en",
        place_id=None,
        stream=True,
    )

    tokens = []
    card_data = None
    async for event in agent.run_chat(req):
        if event["event"] == "token":
            tokens.append(event["data"]["text"])
        elif event["event"] == "card":
            card_data = event["data"]

    answer_text = "".join(tokens)
    assert "pune" not in answer_text.lower(), "Agent defaulted to Pune without user specifying a place"
    assert any(term in answer_text.lower() for term in ["location", "city", "district", "specify", "where"])
    assert card_data is not None
    assert "location" in card_data.get("headline", "").lower() or "clarification" in card_data.get("headline", "").lower()


def test_verifier_rejects_number_not_in_evidence():
    """Grounding verifier must strictly reject answers containing ungrounded numbers."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    packet = EvidencePacket(
        id="test_ep_1",
        source="open_meteo.forecast",
        authority_tier=5,
        provenance="documented-sample",
        issued_at=now,
        valid_from=now,
        valid_to=now,
        place=PlaceReference(id="pune", name="Pune", lat=18.52, lon=73.86),
        values=[
            ValueItem(variable="tmax", value=22.0, unit="degC"),
            ValueItem(variable="rain_sum", value=18.5, unit="mm"),
        ],
        attribution="Open-Meteo",
    )

    # 28.5 is the old hardcoded default; it is NOT in packet
    hallucinated = "Tomorrow in Pune expects 18.5 mm rain and temperature of 28.5 degC."
    res = verify_grounding(hallucinated, [packet])
    assert not res.is_grounded
    assert any("28.5" in r for r in res.reasons)

    # Grounded answer with exact evidence numbers
    grounded = "Tomorrow in Pune expects 18.5 mm rain and temperature of 22.0 degC."
    res2 = verify_grounding(grounded, [packet])
    assert res2.is_grounded
