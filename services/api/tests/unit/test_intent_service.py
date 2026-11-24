"""Unit tests for IntentService and Multilingual SlotParser (Ticket R12)."""
from __future__ import annotations

import pytest

from eval.intent.gold_set_loader import is_gold_set_ready, load_gold_test_set
from ml.intent.service import IntentService
from ml.intent.slot_parser import extract_slots


@pytest.fixture
def intent_service() -> IntentService:
    return IntentService()


def test_intent_service_english_forecast(intent_service: IntentService):
    pred = intent_service.predict("Will it rain tomorrow in Pune?")
    assert pred.intent == "forecast"
    assert 0.0 < pred.confidence <= 1.0
    assert pred.slots.get("place") == "Pune"
    assert pred.slots.get("date_range") == "tomorrow"
    assert pred.model_id in ("intent_classifier_v1.0", "rule-intent-baseline-v1.0")


def test_intent_service_hindi_advisory(intent_service: IntentService):
    pred = intent_service.predict("गेहूं में पहली सिंचाई कब करें?")
    assert pred.intent == "advisory"
    assert pred.slots.get("crop") == "wheat"


def test_intent_service_alert_query(intent_service: IntentService):
    pred = intent_service.predict("Is there any cyclone warning for Odisha coast?")
    assert pred.intent == "alert"
    assert pred.slots.get("hazard") == "cyclone"
    assert pred.slots.get("place") == "Odisha"


def test_intent_service_climate_query(intent_service: IntentService):
    pred = intent_service.predict("How does this May temperature in Jaipur compare to normal?")
    assert pred.intent == "climate_history"
    assert pred.slots.get("place") == "Jaipur"


def test_intent_service_aviation_out_of_domain(intent_service: IntentService):
    pred = intent_service.predict("Can I get the METAR and pilot briefing for flight AI 101?")
    assert pred.intent == "out_of_domain"


def test_slot_parser_across_languages():
    # Bengali
    s_bn = extract_slots("আগামীকাল কলকাতায় ভারী বৃষ্টি হবে কি?")
    assert s_bn.get("place") == "Kolkata"
    assert s_bn.get("date_range") == "tomorrow"
    assert s_bn.get("hazard") == "heavy_rain"

    # Marathi
    s_mr = extract_slots("उद्या पुण्यात उसाच्या पिकासाठी सल्ला काय आहे?")
    assert s_mr.get("place") == "Pune"
    assert s_mr.get("date_range") == "tomorrow"
    assert s_mr.get("crop") == "sugarcane"

    # Telugu
    s_te = extract_slots("రేపు హైదరాబాద్‌లో వర్షం పడుతుందా?")
    assert s_te.get("place") == "Hyderabad"
    assert s_te.get("date_range") == "tomorrow"
    assert s_te.get("hazard") == "rain"

    # Tamil
    s_ta = extract_slots("நாளை சென்னையில் கரும்பு பயிருக்கான வேளாண் ஆலோசனை என்ன?")
    assert s_ta.get("place") == "Chennai"
    assert s_ta.get("date_range") == "tomorrow"
    assert s_ta.get("crop") == "sugarcane"


def test_auto_route_threshold(intent_service: IntentService):
    # Clear weather query should be above or near threshold
    pred_clear = intent_service.predict("What is the weather forecast for Delhi tomorrow?")
    assert pred_clear.confidence >= 0.50

    # Fallback to LLM check
    should_fallback = intent_service.should_fallback_to_llm(pred_clear)
    assert isinstance(should_fallback, bool)


def test_gold_set_loader_unready_behavior():
    # Without human gold queries, loader returns empty list and signals not ready
    queries = load_gold_test_set()
    assert len(queries) < 350
    assert is_gold_set_ready() is False
