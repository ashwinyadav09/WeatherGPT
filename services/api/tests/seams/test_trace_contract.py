from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from packages.contracts.validator import validate_schema
from services.api.app.agent.orchestrator import ChatRequest, Orchestrator
from services.api.app.main import app


def parse_sse_events(body: str) -> list[tuple[str, dict]]:
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    events = []
    current_event = None
    for line in lines:
        if line.startswith("event: "):
            current_event = line.replace("event: ", "").strip()
        elif line.startswith("data: ") and current_event:
            data = json.loads(line.replace("data: ", "").strip())
            events.append((current_event, data))
            current_event = None
    return events


@pytest.mark.asyncio
async def test_trace_contract_forecast_query():
    """Verify trace event emitted during a standard forecast query conforms to schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "session_id": "test_trace_fc",
            "text": "Will it rain tomorrow in Pune?",
            "language": "en",
            "stream": True,
        }
        resp = await client.post("/v1/chat", json=payload)
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        trace_events = [e for e in events if e[0] == "trace"]
        assert len(trace_events) == 1, f"Expected 1 trace event, got {len(trace_events)}"

        trace_data = trace_events[0][1]
        validate_schema("trace_event", trace_data)

        assert trace_data["intent"] == "forecast"
        assert trace_data["confidence"] > 0
        assert trace_data["router_path"] in ["deterministic", "llm_function_call"]
        assert isinstance(trace_data["tools"], list)
        assert len(trace_data["tools"]) >= 1
        assert "name" in trace_data["tools"][0]
        assert "latency_ms" in trace_data["tools"][0]
        assert isinstance(trace_data["models"], list)
        assert isinstance(trace_data["verifier"], dict)
        assert "passed" in trace_data["verifier"]
        assert "checked_numbers" in trace_data["verifier"]
        assert "failures" in trace_data["verifier"]
        assert isinstance(trace_data["llm"], dict)
        assert "provider" in trace_data["llm"]
        assert "model" in trace_data["llm"]


@pytest.mark.asyncio
async def test_trace_contract_evacuation_safety_guard():
    """Verify trace event emitted when evacuation pre-guard triggers conforms to schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "session_id": "test_trace_evac",
            "text": "Do I need to evacuate my house because of the flood?",
            "language": "en",
            "stream": True,
        }
        resp = await client.post("/v1/chat", json=payload)
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        trace_events = [e for e in events if e[0] == "trace"]
        assert len(trace_events) == 1

        trace_data = trace_events[0][1]
        validate_schema("trace_event", trace_data)
        assert trace_data["intent"] == "safety_redirect"
        assert trace_data["router_path"] == "safety_guard"
        assert trace_data["confidence"] == 1.0


@pytest.mark.asyncio
async def test_trace_contract_pesticide_safety_guard():
    """Verify trace event emitted when pesticide pre-guard triggers conforms to schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "session_id": "test_trace_pest",
            "text": "What pesticide dosage should I apply for crop disease?",
            "language": "en",
            "stream": True,
        }
        resp = await client.post("/v1/chat", json=payload)
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        trace_events = [e for e in events if e[0] == "trace"]
        assert len(trace_events) == 1

        trace_data = trace_events[0][1]
        validate_schema("trace_event", trace_data)
        assert trace_data["intent"] == "safety_redirect"
        assert trace_data["router_path"] == "safety_guard"


@pytest.mark.asyncio
async def test_trace_contract_aviation_declined():
    """Verify trace event emitted when aviation brief is requested conforms to schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "session_id": "test_trace_av",
            "text": "Give me METAR and TAF briefing for Delhi airport",
            "language": "en",
            "stream": True,
        }
        resp = await client.post("/v1/chat", json=payload)
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        trace_events = [e for e in events if e[0] == "trace"]
        assert len(trace_events) == 1

        trace_data = trace_events[0][1]
        validate_schema("trace_event", trace_data)
        assert trace_data["intent"] == "aviation_brief"
        assert trace_data["router_path"] == "policy_check"


@pytest.mark.asyncio
async def test_trace_contract_location_prompt():
    """Verify trace event emitted when query lacks a place conforms to schema."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "session_id": "test_trace_noplace",
            "text": "What is the temperature today?",
            "language": "en",
            "stream": True,
        }
        resp = await client.post("/v1/chat", json=payload)
        assert resp.status_code == 200

        events = parse_sse_events(resp.text)
        trace_events = [e for e in events if e[0] == "trace"]
        assert len(trace_events) == 1

        trace_data = trace_events[0][1]
        validate_schema("trace_event", trace_data)
        assert trace_data["intent"] == "clarification"
        assert trace_data["router_path"] == "location_resolver"


@pytest.mark.asyncio
async def test_trace_contract_verifier_failure_path():
    """Verify trace event when LLM hallucinates and fallback template is used."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value={"content": "In Pune tomorrow expects 999.0 mm rain and 88.0 degC temperature."})
    mock_llm.last_call_metrics = {
        "provider": "mock_groq",
        "model": "llama-3.3-70b-versatile",
        "prompt_tokens": 150,
        "completion_tokens": 40,
    }

    orchestrator = Orchestrator(llm_gateway=mock_llm)
    req = ChatRequest(
        session_id="test_trace_verifier_fail",
        text="Will it rain tomorrow in Pune?",
        language="en",
    )

    events = [e async for e in orchestrator.handle_chat_stream(req)]
    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1

    trace_data = trace_events[0]["data"]
    validate_schema("trace_event", trace_data)

    # Verifier failures should be recorded and fallback_used marked True
    assert trace_data["verifier"]["fallback_used"] is True
    assert len(trace_data["verifier"]["failures"]) > 0
    assert trace_data["verifier"]["passed"] is True  # Passed after template fallback
