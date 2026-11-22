"""Unit tests for Orchestrator (Ticket R2.3 & R2.4).

Requirements:
- services/api/app/agent/orchestrator.py
- Replaces fixed template agent with tool-calling, grounded and verified orchestrator.
- Safety pre-guards (evacuation, pesticide).
- Aviation briefing politely declined (decision D3).
- Uses LLMGateway and tools (geocode, get_forecast, get_alerts, get_climate, search_knowledge).
- Grounding verification: on ungrounded numbers, retries and falls back to vetted template.
- Emits SSE events: meta, evidence, token, card, trace (R2.4), done.
- Session context (place, date) with TTL.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from services.api.app.agent.orchestrator import ChatRequest, Orchestrator
from services.api.app.gateways.llm.adapters.stub import StubLLMAdapter
from services.api.app.gateways.llm.gateway import LLMGateway


@pytest.mark.asyncio
async def test_orchestrator_forecast_flow_and_trace_event() -> None:
    orchestrator = Orchestrator(llm=LLMGateway(primary=StubLLMAdapter()))
    req = ChatRequest(
        session_id="test_orch_1",
        text="Will it rain tomorrow in Pune?",
        language="en",
        stream=True,
    )

    events: list[dict] = []
    async for evt in orchestrator.run_chat(req):
        events.append(evt)

    event_types = [e["event"] for e in events]
    assert "meta" in event_types
    assert "evidence" in event_types
    assert "token" in event_types
    assert "card" in event_types
    assert "trace" in event_types
    assert "done" in event_types

    # Inspect trace event (R2.4)
    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1
    trace_data = trace_events[0]["data"]
    assert "intent" in trace_data
    assert "confidence" in trace_data
    assert "router_path" in trace_data
    assert "tools" in trace_data
    assert isinstance(trace_data["tools"], list)
    assert len(trace_data["tools"]) >= 1
    assert "verifier" in trace_data
    assert trace_data["verifier"]["passed"] is True
    assert "llm" in trace_data


@pytest.mark.asyncio
async def test_orchestrator_evacuation_safety_redirect() -> None:
    orchestrator = Orchestrator()
    req = ChatRequest(
        session_id="test_evac_1",
        text="Should I evacuate my house immediately?",
        language="en",
    )

    tokens = []
    card = None
    trace = None
    async for evt in orchestrator.run_chat(req):
        if evt["event"] == "token":
            tokens.append(evt["data"]["text"])
        elif evt["event"] == "card":
            card = evt["data"]
        elif evt["event"] == "trace":
            trace = evt["data"]

    full_ans = "".join(tokens)
    assert "112" in full_ans or "1077" in full_ans or "local authorities" in full_ans.lower()
    assert card is not None
    assert trace is not None
    assert trace["intent"] == "safety_redirect"


@pytest.mark.asyncio
async def test_orchestrator_pesticide_safety_redirect() -> None:
    orchestrator = Orchestrator()
    req = ChatRequest(
        session_id="test_pest_1",
        text="What is the chemical pesticide dose for wheat rust?",
        language="en",
    )

    tokens = []
    async for evt in orchestrator.run_chat(req):
        if evt["event"] == "token":
            tokens.append(evt["data"]["text"])

    full_ans = "".join(tokens)
    assert "1800-180-1551" in full_ans or "kisan" in full_ans.lower()


@pytest.mark.asyncio
async def test_orchestrator_aviation_query_unsupported() -> None:
    orchestrator = Orchestrator()
    req = ChatRequest(
        session_id="test_av_1",
        text="Can you give me an aviation briefing for VIDP METAR?",
        language="en",
    )

    tokens = []
    trace = None
    async for evt in orchestrator.run_chat(req):
        if evt["event"] == "token":
            tokens.append(evt["data"]["text"])
        elif evt["event"] == "trace":
            trace = evt["data"]

    full_ans = "".join(tokens)
    assert "aviation" in full_ans.lower()
    assert "not supported" in full_ans.lower()
    assert trace is not None
    assert trace["intent"] == "aviation_brief"


@pytest.mark.asyncio
async def test_orchestrator_verifier_failure_triggers_template_fallback() -> None:
    """When LLM hallucinates numbers not in evidence, verifier fails and falls back to template."""
    mock_hallucinating_llm = AsyncMock()
    # Returns 999.9 mm and 88.8 °C (clearly hallucinated numbers)
    mock_hallucinating_llm.complete.return_value = {
        "role": "assistant",
        "content": "Tomorrow in Pune it will rain 999.9 mm with a temperature of 88.8 degC.",
    }
    gateway = LLMGateway(primary=mock_hallucinating_llm)

    orchestrator = Orchestrator(llm=gateway)
    req = ChatRequest(
        session_id="test_hallucinate_1",
        text="Will it rain tomorrow in Pune?",
        language="en",
    )

    tokens = []
    trace = None
    async for evt in orchestrator.run_chat(req):
        if evt["event"] == "token":
            tokens.append(evt["data"]["text"])
        elif evt["event"] == "trace":
            trace = evt["data"]

    ans = "".join(tokens)
    # The hallucinated numbers 999.9 and 88.8 must NOT be in the final answer
    assert "999.9" not in ans
    assert "88.8" not in ans
    assert trace is not None
    assert trace["verifier"]["fallback_used"] is True


@pytest.mark.asyncio
async def test_orchestrator_session_context_place_memory() -> None:
    orchestrator = Orchestrator(llm=LLMGateway(primary=StubLLMAdapter()))
    session_id = "test_memory_session_1"

    # Turn 1: user mentions Pune
    req1 = ChatRequest(
        session_id=session_id,
        text="Will it rain tomorrow in Pune?",
        language="en",
    )
    async for _ in orchestrator.run_chat(req1):
        pass

    # Turn 2: user asks follow-up without mentioning place
    req2 = ChatRequest(
        session_id=session_id,
        text="What will the temperature be?",
        language="en",
    )
    tokens = []
    card = None
    async for evt in orchestrator.run_chat(req2):
        if evt["event"] == "token":
            tokens.append(evt["data"]["text"])
        elif evt["event"] == "card":
            card = evt["data"]

    # Orchestrator remembered Pune from Turn 1
    assert card is not None
    assert "Pune" in card["headline"] or "pune" in card["source_line"].lower()
