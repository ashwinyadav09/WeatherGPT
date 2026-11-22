"""Unit tests for Agent Tools (Ticket R2.1).

Requirements:
- services/api/app/agent/tools.py
- Tools: geocode(text), get_forecast(place, day|range), get_alerts(place),
  get_climate(place, metric, period), get_risk_outlook(place), search_knowledge(query, lang).
- Every tool returns evidence packets with source, provenance, issued and valid times,
  units and attribution.
- Tools NEVER raise raw provider errors to the LLM; failures are captured in structured evidence.
"""
from __future__ import annotations

import pytest

from services.api.app.agent.tools import (
    TOOL_SCHEMAS,
    call_tool,
    geocode,
    get_alerts,
    get_climate,
    get_forecast,
    get_risk_outlook,
    search_knowledge,
)
from services.api.app.evidence.models import EvidencePacket


@pytest.mark.asyncio
async def test_geocode_tool() -> None:
    # 1. Known place
    packets = await geocode(text="Pune")
    assert isinstance(packets, list)
    assert len(packets) >= 1
    pkt = packets[0]
    assert isinstance(pkt, EvidencePacket)
    assert pkt.place.name.lower() == "pune" or "pune" in pkt.place.id.lower()
    assert abs(pkt.place.lat - 18.5204) < 0.1
    assert abs(pkt.place.lon - 73.8567) < 0.1
    assert pkt.attribution != ""

    # 2. Unknown place must return structured packet, not raise
    unknown_packets = await geocode(text="NonExistentPlaceXYZ99999")
    assert isinstance(unknown_packets, list)
    assert len(unknown_packets) >= 1
    unk_pkt = unknown_packets[0]
    assert isinstance(unk_pkt, EvidencePacket)
    vars_found = {v.variable: v.value for v in unk_pkt.values}
    assert vars_found.get("status") == "not_found"


@pytest.mark.asyncio
async def test_get_forecast_tool_days_and_range() -> None:
    # 1. Day 0 (today)
    today_packets = await get_forecast(place="Pune", day=0)
    assert isinstance(today_packets, list)
    assert len(today_packets) >= 1
    for p in today_packets:
        assert isinstance(p, EvidencePacket)
        assert p.place.name.lower() == "pune" or "pune" in p.place.id.lower()
        assert p.attribution != ""

    # 2. Day 1 ("tomorrow")
    tomorrow_packets = await get_forecast(place="Pune", day=1)
    assert isinstance(tomorrow_packets, list)
    assert len(tomorrow_packets) >= 1
    daily_pkt = tomorrow_packets[0]
    assert isinstance(daily_pkt, EvidencePacket)
    # Step should be 1
    step_vals = [v.step for v in daily_pkt.values if v.step is not None]
    if step_vals:
        assert 1 in step_vals

    # 3. String day ("tomorrow")
    tomorrow_str_packets = await get_forecast(place="Pune", day="tomorrow")
    assert len(tomorrow_str_packets) >= 1

    # 4. Range of days
    range_packets = await get_forecast(place="Pune", day=None, range_days=3)
    assert len(range_packets) >= 2


@pytest.mark.asyncio
async def test_get_alerts_tool() -> None:
    # Alerts tool returns active alerts or a clear no-alerts evidence packet
    packets = await get_alerts(place="Pune")
    assert isinstance(packets, list)
    assert len(packets) >= 1
    pkt = packets[0]
    assert isinstance(pkt, EvidencePacket)
    assert pkt.authority_tier == 1
    assert "sachet" in pkt.attribution.lower() or "sachet" in pkt.source.lower()
    vars_found = {v.variable: v.value for v in pkt.values}
    assert "hazard" in vars_found or "active_alerts_count" in vars_found or "status" in vars_found


@pytest.mark.asyncio
async def test_get_climate_tool() -> None:
    packets = await get_climate(place="Pune", metric="rain", period="2026-05", statistic="normal")
    assert isinstance(packets, list)
    assert len(packets) >= 1
    pkt = packets[0]
    assert isinstance(pkt, EvidencePacket)
    assert "era5" in pkt.source.lower() or "era5" in pkt.attribution.lower()
    vars_found = {v.variable for v in pkt.values}
    assert any("normal" in v or "anomaly" in v or "rain" in v for v in vars_found)


@pytest.mark.asyncio
async def test_get_risk_outlook_tool() -> None:
    packets = await get_risk_outlook(place="Pune")
    assert isinstance(packets, list)
    assert len(packets) >= 1
    pkt = packets[0]
    assert isinstance(pkt, EvidencePacket)
    vars_found = {v.variable: v.value for v in pkt.values}
    assert any("risk" in v for v in vars_found)
    # Attribution must state it is experimental or not an official warning
    assert "official warning" in pkt.attribution.lower() or "experimental" in pkt.attribution.lower()


@pytest.mark.asyncio
async def test_search_knowledge_tool() -> None:
    # 1. English search
    en_packets = await search_knowledge(query="heat wave drinking water", lang="en")
    assert isinstance(en_packets, list)
    assert len(en_packets) >= 1
    pkt = en_packets[0]
    assert isinstance(pkt, EvidencePacket)
    assert "ndma" in pkt.source.lower() or "guideline" in pkt.source.lower() or "official" in pkt.source.lower()
    guidance_text = " ".join(str(v.value) for v in pkt.values)
    assert len(guidance_text) > 10

    # 2. Hindi search
    hi_packets = await search_knowledge(query="लू में क्या सावधानी बरतें", lang="hi")
    assert isinstance(hi_packets, list)
    assert len(hi_packets) >= 1


@pytest.mark.asyncio
async def test_call_tool_dispatcher_and_schemas() -> None:
    # Verify tool schemas format
    assert isinstance(TOOL_SCHEMAS, list)
    tool_names = [t["function"]["name"] for t in TOOL_SCHEMAS]
    expected_names = [
        "geocode",
        "get_forecast",
        "get_alerts",
        "get_climate",
        "get_risk_outlook",
        "search_knowledge",
    ]
    for name in expected_names:
        assert name in tool_names, f"Tool {name} missing in TOOL_SCHEMAS"

    # Call tool via dispatcher
    res = await call_tool(name="geocode", args={"text": "Mumbai"})
    assert isinstance(res, list)
    assert len(res) >= 1
    assert "mumbai" in res[0].place.name.lower() or "mumbai" in res[0].place.id.lower()

    # Calling an unknown tool returns error packet, never raises
    err_res = await call_tool(name="unknown_tool_xyz", args={})
    assert isinstance(err_res, list)
    assert len(err_res) == 1
    assert any(v.variable == "error" for v in err_res[0].values)
