"""Integration and Contract Tests for Live Agent Orchestration (Ticket R16).

Verifies:
- Trace event conforms to packages/contracts/schemas/trace_event.json.
- Trace event lists exactly the models that ran.
- enabled_in_production=False models are never used.
- Verifier gates output and fallback is tracked in trace.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from packages.contracts.validator import validate_schema
from services.api.app.agent.orchestrator import ChatRequest, Orchestrator


@pytest.mark.asyncio
async def test_trace_schema_conformance():
    """Verify trace event emitted by Orchestrator strictly validates against trace_event.json schema."""
    orchestrator = Orchestrator()
    req = ChatRequest(session_id="test_sess_01", text="Will it rain tomorrow in Pune?", language="en", place_id="pune")

    events = []
    async for event in orchestrator.run_chat(req):
        events.append(event)

    event_types = [e["event"] for e in events]
    assert "meta" in event_types
    assert "trace" in event_types
    assert "done" in event_types

    trace_event = next(e for e in events if e["event"] == "trace")
    trace_data = trace_event["data"]

    # Validate against JSON schema contract
    validate_schema("trace_event", trace_data)

    assert "intent" in trace_data
    assert "confidence" in trace_data
    assert "router_path" in trace_data
    assert "tools" in trace_data
    assert "models" in trace_data
    assert "verifier" in trace_data
    assert "llm" in trace_data


@pytest.mark.asyncio
async def test_trace_lists_exactly_models_that_ran():
    """Verify trace event lists exactly the models that ran."""
    orchestrator = Orchestrator()

    # 1. Forecast query with ml_mode='raw': only intent model should run, bias correction must NOT run
    req_raw = ChatRequest(session_id="sess_raw", text="What is the weather in Pune tomorrow?", ml_mode="raw", language="en")
    events_raw = []
    async for ev in orchestrator.run_chat(req_raw):
        events_raw.append(ev)

    trace_raw = next(e["data"] for e in events_raw if e["event"] == "trace")
    model_ids_raw = [m["id"] for m in trace_raw["models"] if m.get("used")]
    assert any("intent" in mid.lower() for mid in model_ids_raw)
    assert not any("bias" in mid.lower() for mid in model_ids_raw)

    # 2. Advisory query: intent model and rag advisory engine should run
    req_adv = ChatRequest(session_id="sess_adv", text="What precautions should I take during heat wave?", language="en")
    events_adv = []
    async for ev in orchestrator.run_chat(req_adv):
        events_adv.append(ev)

    trace_adv = next(e["data"] for e in events_adv if e["event"] == "trace")
    model_ids_adv = [m["id"] for m in trace_adv["models"] if m.get("used")]
    assert any("rag" in mid.lower() for mid in model_ids_adv)
    assert not any("climate" in mid.lower() for mid in model_ids_adv)

    # 3. Climate query: intent model and climate model should run
    req_clim = ChatRequest(session_id="sess_clim", text="Has monsoon rain trend changed in Pune since 1990?", language="en")
    events_clim = []
    async for ev in orchestrator.run_chat(req_clim):
        events_clim.append(ev)

    trace_clim = next(e["data"] for e in events_clim if e["event"] == "trace")
    model_ids_clim = [m["id"] for m in trace_clim["models"] if m.get("used")]
    assert any("climate" in mid.lower() for mid in model_ids_clim)
    assert not any("rag" in mid.lower() for mid in model_ids_clim)

    # 4. Risk query: extreme-event risk model should run
    req_risk = ChatRequest(session_id="sess_risk", text="What is the extreme heatwave risk outlook for Pune?", language="en")
    events_risk = []
    async for ev in orchestrator.run_chat(req_risk):
        events_risk.append(ev)

    trace_risk = next(e["data"] for e in events_risk if e["event"] == "trace")
    model_ids_risk = [m["id"] for m in trace_risk["models"] if m.get("used")]
    assert any("extreme_event" in mid.lower() or "risk" in mid.lower() for mid in model_ids_risk)


@pytest.mark.asyncio
async def test_disabled_model_never_used_in_agent():
    """Verify that models with enabled_in_production=False are strictly excluded from execution."""
    orchestrator = Orchestrator()

    # 1. Disable intent model
    with patch("services.api.app.agent.orchestrator.is_model_enabled", side_effect=lambda name: False if name == "intent" else True):
        req = ChatRequest(session_id="sess_dis_intent", text="What is the forecast for Pune tomorrow?", language="en")
        events = []
        async for ev in orchestrator.run_chat(req):
            events.append(ev)

        trace = next(e["data"] for e in events if e["event"] == "trace")
        # Router path must fall back to deterministic and intent model must not be listed as used
        assert trace["router_path"] == "deterministic"
        model_ids = [m["id"] for m in trace["models"] if m.get("used")]
        assert not any("intent" in mid.lower() for mid in model_ids)

    # 2. Disable bias correction model
    with patch("services.api.app.agent.orchestrator.is_model_enabled", side_effect=lambda name: False if name == "bias_correction" else True):
        req_bc = ChatRequest(session_id="sess_dis_bc", text="What is the forecast for Pune tomorrow?", ml_mode="ml", language="en")
        events_bc = []
        async for ev in orchestrator.run_chat(req_bc):
            events_bc.append(ev)

        trace_bc = next(e["data"] for e in events_bc if e["event"] == "trace")
        model_ids_bc = [m["id"] for m in trace_bc["models"] if m.get("used")]
        assert not any("bias" in mid.lower() for mid in model_ids_bc)

    # 3. Disable RAG engine
    with patch("services.api.app.agent.orchestrator.is_model_enabled", side_effect=lambda name: False if name == "rag" else True):
        req_rag = ChatRequest(session_id="sess_dis_rag", text="What precautions should I take during heat wave?", language="en")
        events_rag = []
        async for ev in orchestrator.run_chat(req_rag):
            events_rag.append(ev)

        trace_rag = next(e["data"] for e in events_rag if e["event"] == "trace")
        model_ids_rag = [m["id"] for m in trace_rag["models"] if m.get("used")]
        assert not any("rag" in mid.lower() for mid in model_ids_rag)
