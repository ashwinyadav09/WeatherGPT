from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from packages.contracts.validator import validate_schema
from services.api.app.agent.orchestrator import ChatRequest, Orchestrator
from services.api.app.modules.location.resolver import LocationResolver

LIGHTNING_QUESTIONS = {
    "en": "What safety rules should I follow during lightning and thunderstorms?",
    "hi": "आकाशीय बिजली और तूफान के समय क्या सावधानियां बरतनी चाहिए?",
    "bn": "বজ্রপাতের সময় কী কী নিরাপত্তা নিয়ম মেনে চলা উচিত?",
    "mr": "विजांचा कडकडाट आणि वादळाच्या वेळी कोणते सुरक्षा नियम पाळावेत?",
    "te": "ఉరుములు, మెరుపుల సమయంలో ఎలాంటి రక్షణ చర్యలు పాటించాలి?",
    "ta": "இடி மின்னல் மற்றும் புயலின் போது பின்பற்ற வேண்டிய பாதுகாப்பு விதிகள் என்ன?",
    "or": "ବଜ୍ରପାତ ଏବଂ ଝଡ଼ ସମୟରେ କେଉଁ ନିରାପତ୍ତା ନିୟମ ମାନିବା ଉଚିତ?",
}

OTHER_HAZARD_QUESTIONS = [
    ("en", "What precautions should I take during a severe heatwave?"),
    ("en", "What is the official advisory for severe coldwave?"),
    ("en", "What should citizens do during urban flood waterlogging?"),
    ("en", "What precautions should be taken when a cyclone warning is issued?"),
    ("en", "What is the agriculture advisory for crop protection during harsh weather?"),
    ("hi", "भीषण लू से बचाव के लिए क्या उपाय करने चाहिए?"),
    ("hi", "शीतलहर से सुरक्षा के लिए आधिकारिक सलाह क्या है?"),
    ("hi", "मौसम खराब होने पर फसलों की सुरक्षा के लिए क्या कृषि सलाह है?"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("lang,question", list(LIGHTNING_QUESTIONS.items()))
async def test_lightning_question_routes_to_advisory_and_never_place_resolution(lang: str, question: str):
    """Hazard-safety lightning question must route to advisory path and NEVER call place resolution (R20.5)."""
    mock_resolver = AsyncMock(spec=LocationResolver)
    mock_resolver.resolve = AsyncMock()

    orchestrator = Orchestrator(location_resolver=mock_resolver)
    req = ChatRequest(
        session_id=f"lightning_reg_{lang}",
        text=question,
        language=lang,
    )

    events = [e async for e in orchestrator.handle_chat_stream(req)]

    # 1. Location resolver was NEVER invoked on question text
    mock_resolver.resolve.assert_not_called()

    # 2. Trace asserts
    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1, "Expected exactly 1 trace event"
    trace = trace_events[0]["data"]
    validate_schema("trace_event", trace)

    assert trace["intent"] == "advisory", f"Expected advisory intent, got {trace['intent']}"

    # 3. Answer and card do NOT contain question text as place name (Finding V5 regression)
    card_events = [e for e in events if e["event"] == "card"]
    assert len(card_events) >= 1
    card = card_events[0]["data"]

    full_answer = "".join(e["data"]["text"] for e in events if e["event"] == "token")

    # The question text itself must never be treated as a place name
    assert question not in card.get("headline", ""), f"Card headline treated question text as place: {card.get('headline')}"
    assert f"weather information is available for {question}" not in full_answer
    assert f"According to NDMA SACHET, weather information is available for {question}" not in full_answer

    # 4. In fallback mode (LLM disabled), advisory does NOT dump raw internal chunk ids like [chunk_id]
    import re
    # Must not start with raw chunk id like [en_ndma_lightning_safety_01]
    assert not re.search(r"^\[[a-z0-9_\-]+\]", full_answer.strip()), f"Answer contains raw chunk ID dump: {full_answer}"


@pytest.mark.asyncio
@pytest.mark.parametrize("lang,question", OTHER_HAZARD_QUESTIONS)
async def test_hazard_safety_advice_questions_bypass_place_resolution(lang: str, question: str):
    """Heatwave, coldwave, flood, cyclone, crop protection questions route to advisory without place resolution."""
    mock_resolver = AsyncMock(spec=LocationResolver)
    mock_resolver.resolve = AsyncMock()

    orchestrator = Orchestrator(location_resolver=mock_resolver)
    req = ChatRequest(
        session_id=f"hazard_reg_{lang}",
        text=question,
        language=lang,
    )

    events = [e async for e in orchestrator.handle_chat_stream(req)]

    # Resolver must never be called on question text
    mock_resolver.resolve.assert_not_called()

    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1
    trace = trace_events[0]["data"]
    assert trace["intent"] == "advisory"


@pytest.mark.asyncio
async def test_trace_confidence_is_null_when_no_ml_model_ran():
    """Confidence in trace must be null when no ML model ran (T1/T2, R20.5)."""
    orchestrator = Orchestrator(intent_model=None)
    req = ChatRequest(
        session_id="trace_conf_null",
        text="What safety rules should I follow during lightning and thunderstorms?",
        language="en",
    )
    events = [e async for e in orchestrator.handle_chat_stream(req)]
    trace_events = [e for e in events if e["event"] == "trace"]
    assert len(trace_events) == 1
    trace = trace_events[0]["data"]
    assert trace["confidence"] is None, f"Expected confidence to be None/null, got {trace['confidence']}"


@pytest.mark.asyncio
async def test_advisory_fallback_shows_quoted_extract_with_source_and_page():
    """With LLM disabled, advisory fallback shows quoted extract with source and page, not raw chunk dump."""
    orchestrator = Orchestrator()
    req = ChatRequest(
        session_id="advisory_fallback_format",
        text="What safety rules should I follow during lightning and thunderstorms?",
        language="en",
    )
    events = [e async for e in orchestrator.handle_chat_stream(req)]
    full_answer = "".join(e["data"]["text"] for e in events if e["event"] == "token")

    # Should have quoted extract and source
    assert '"' in full_answer, f"Expected quoted extract in fallback answer: {full_answer}"
    assert "NDMA" in full_answer or "IMD" in full_answer, f"Expected source in fallback answer: {full_answer}"
