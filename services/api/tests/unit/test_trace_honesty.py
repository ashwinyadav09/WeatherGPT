from __future__ import annotations

import types
from typing import Any
from unittest.mock import AsyncMock

import pytest

from packages.contracts.validator import validate_schema
from services.api.app.agent.orchestrator import ChatRequest, Orchestrator


def verify_trace_model_honesty(trace: dict[str, Any], actually_invoked_model_ids: set[str]) -> None:
    """Validate that every model listed in trace['models'] was actually invoked."""
    reported_models = {m["id"] for m in trace.get("models", [])}
    uninvoked = reported_models - actually_invoked_model_ids
    if uninvoked:
        raise AssertionError(f"Dishonest trace: trace names models that were never invoked: {uninvoked}")


@pytest.mark.asyncio
async def test_trace_deterministic_path_honesty():
    """Deterministic routing without intent model produces empty models list and null confidence."""
    orchestrator = Orchestrator(intent_model=None)
    req = ChatRequest(
        session_id="honesty_test_det",
        text="Will it rain tomorrow in Pune?",
        language="en",
    )
    events = [e async for e in orchestrator.handle_chat_stream(req)]
    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1

    trace = trace_events[0]["data"]
    validate_schema("trace_event", trace)

    # Truthfulness assertions
    assert trace["models"] == [], "Models list must be empty when no model was invoked"
    assert trace["confidence"] is None, "Confidence must be null/None when no model produced a probability"
    assert trace["router_path"] == "deterministic"

    # Verify honesty check passes
    verify_trace_model_honesty(trace, actually_invoked_model_ids=set())


@pytest.mark.asyncio
async def test_trace_intent_model_invoked_honesty():
    """When an intent model is invoked, trace names exactly that model and its output confidence."""
    invoked_models: set[str] = set()

    class FakeIntentModel:
        MODEL_ID = "rule_intent_baseline"
        MODEL_VERSION = "v1.0"

        def predict(self, text: str):
            invoked_models.add(self.MODEL_ID)
            return types.SimpleNamespace(intent="forecast", confidence=0.87)

    intent_model = FakeIntentModel()
    orchestrator = Orchestrator(intent_model=intent_model)

    req = ChatRequest(
        session_id="honesty_test_model",
        text="Will it rain tomorrow in Pune?",
        language="en",
    )
    events = [e async for e in orchestrator.handle_chat_stream(req)]
    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1

    trace = trace_events[0]["data"]
    validate_schema("trace_event", trace)

    assert "rule_intent_baseline" in invoked_models
    assert len(trace["models"]) == 1
    assert trace["models"][0]["id"] == "rule_intent_baseline"
    assert trace["models"][0]["version"] == "v1.0"
    assert trace["models"][0]["used"] is True
    assert trace["confidence"] == pytest.approx(0.87, abs=1e-4)
    assert trace["router_path"] == "intent_model"

    # Honesty check passes when actual matches reported
    verify_trace_model_honesty(trace, actually_invoked_model_ids=invoked_models)


def test_honesty_check_fails_if_trace_names_uninvoked_model():
    """Done condition: a test fails if the trace names a model that was not invoked."""
    dishonest_trace = {
        "intent": "forecast",
        "confidence": 0.95,
        "router_path": "deterministic",
        "tools": [],
        "models": [
            {"id": "phantom_neural_intent_v2", "version": "v2.0", "used": True},
        ],
        "verifier": {"passed": True, "checked_numbers": [], "failures": [], "fallback_used": False},
        "llm": {"provider": "mock", "model": "test", "tokens_in": 0, "tokens_out": 0},
    }

    # Model 'phantom_neural_intent_v2' was never invoked
    actually_invoked: set[str] = set()

    with pytest.raises(AssertionError, match="Dishonest trace: trace names models that were never invoked: {'phantom_neural_intent_v2'}"):
        verify_trace_model_honesty(dishonest_trace, actually_invoked)


@pytest.mark.asyncio
async def test_trace_llm_provider_reflects_actual_adapter():
    """trace.llm.provider must reflect the actual answering adapter, never hardcoded to groq."""
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value={"content": "Rain is 0.0 mm in Pune tomorrow."})
    mock_llm.last_call_metrics = {
        "provider": "openrouter_free_tier",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "prompt_tokens": 120,
        "completion_tokens": 25,
    }

    orchestrator = Orchestrator(llm_gateway=mock_llm)
    req = ChatRequest(
        session_id="honesty_test_llm",
        text="Will it rain tomorrow in Pune?",
        language="en",
    )
    events = [e async for e in orchestrator.handle_chat_stream(req)]
    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1

    trace = trace_events[0]["data"]
    validate_schema("trace_event", trace)

    assert trace["llm"]["provider"] == "openrouter_free_tier"
    assert trace["llm"]["model"] == "meta-llama/llama-3.3-70b-instruct:free"
    assert trace["llm"]["tokens_in"] == 120
    assert trace["llm"]["tokens_out"] == 25


@pytest.mark.asyncio
async def test_trace_pre_guard_refusal_honest_trace():
    """Pre-guard safety query emits router_path=safety_guard, provider=none, and empty models."""
    orchestrator = Orchestrator()
    req = ChatRequest(
        session_id="honesty_test_guard",
        text="Should I evacuate my house immediately due to flood?",
        language="en",
    )
    events = [e async for e in orchestrator.handle_chat_stream(req)]
    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1

    trace = trace_events[0]["data"]
    validate_schema("trace_event", trace)

    assert trace["intent"] == "safety_redirect"
    assert trace["router_path"] == "safety_guard"
    assert trace["models"] == []
    assert trace["llm"]["provider"] == "none"
    assert trace["llm"]["tokens_in"] == 0
