"""Seam tests for Intent and Slot classification model (Ticket 15)."""

from __future__ import annotations

import time

import pytest

from ml.intent.model import IntentSlotModel


@pytest.fixture
def intent_model() -> IntentSlotModel:
    return IntentSlotModel()


def test_intent_accuracy_on_golden_set(intent_model: IntentSlotModel):
    golden_cases = intent_model.load_golden_set()
    assert len(golden_cases) >= 300, "Golden test set must have at least 300 cases"

    correct = 0
    for case in golden_cases:
        res = intent_model.predict(case["text"])
        if res.intent == case["expected_intent"]:
            correct += 1

    accuracy = (correct / len(golden_cases)) * 100.0
    print(f"\nGolden set accuracy: {accuracy:.2f}% ({correct}/{len(golden_cases)})")
    assert accuracy >= 95.0, f"Intent accuracy must be >= 95%, got {accuracy:.2f}%"


def test_slot_extraction(intent_model: IntentSlotModel):
    # Test place and time slot extraction in English
    res1 = intent_model.predict("Will it rain tomorrow in Pune?")
    assert res1.intent == "forecast"
    assert res1.slots.get("place") == "Pune"
    assert "tomorrow" in res1.slots.get("time_window", "").lower()

    # Test Hindi slot extraction
    res2 = intent_model.predict("क्या कल दिल्ली में बारिश होगी?")
    assert res2.intent == "forecast"
    assert "दिल्ली" in res2.slots.get("place", "") or res2.slots.get("place") == "Delhi"

    # Test Advisory & Crop slot extraction
    res3 = intent_model.predict("पुणे में गन्ने की फसल के लिए क्या सलाह है?")
    assert res3.intent == "advisory"
    assert res3.slots.get("crop") in ("गन्ना", "sugarcane")

    # Test Climate question
    res4 = intent_model.predict("How does this May temperature in Jaipur compare to normal?")
    assert res4.intent == "climate"
    assert res4.slots.get("place") == "Jaipur"


def test_low_confidence_fallback_to_llm(intent_model: IntentSlotModel):
    # Completely ambiguous or gibberish input should have low confidence
    res = intent_model.predict("xyz abc random gibberish 12345")
    assert res.confidence < 0.70
    assert intent_model.should_fallback_to_llm(res, threshold=0.75) is True

    # Clear query should have high confidence and not fallback
    res_clear = intent_model.predict("What is the current temperature in Mumbai?")
    assert res_clear.confidence >= 0.85
    assert intent_model.should_fallback_to_llm(res_clear, threshold=0.75) is False


def test_inference_latency_in_milliseconds(intent_model: IntentSlotModel):
    text = "Is there an alert for heavy rain in Mumbai right now?"

    # Warmup
    intent_model.predict(text)

    latencies_ms = []
    for _ in range(50):
        t0 = time.perf_counter()
        intent_model.predict(text)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)

    avg_ms = sum(latencies_ms) / len(latencies_ms)
    print(f"\nAverage inference latency: {avg_ms:.2f} ms")
    assert avg_ms < 15.0, f"Inference must complete in milliseconds (< 15ms), took {avg_ms:.2f}ms"
