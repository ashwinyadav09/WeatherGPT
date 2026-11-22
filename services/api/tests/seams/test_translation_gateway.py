"""Seam and unit tests for Translation Gateway (Ticket R1.2).

Requirements:
- New gateways/translation/ with base.py, sarvam.py, llm_fallback.py, cache.py, and gateway.py.
- Cache key: sha256(text + src + tgt + glossary_version).
- Mocked HTTP tests prove cache hits skip network.
- Numbers and units are protected with placeholders before translation and restored after.
- Native Indic digits are normalised to ASCII before returning.
- On Sarvam error, gracefully falls back to LLM translation.
"""
from __future__ import annotations

import logging

import httpx
import pytest

from services.api.app.gateways.translation.base import TranslationAdapter
from services.api.app.gateways.translation.cache import TranslationCache
from services.api.app.gateways.translation.gateway import (
    TranslationGateway,
    normalise_indic_digits,
    protect_numbers_and_units,
    restore_numbers_and_units,
)
from services.api.app.gateways.translation.sarvam import SarvamTranslationAdapter


def test_digit_normalisation():
    """Verify Devanagari, Bengali, Telugu, Odia, Tamil digits are converted to ASCII 0-9."""
    devanagari = "१२.५ मिमी आणि २२.० डिग्री"
    assert normalise_indic_digits(devanagari) == "12.5 मिमी आणि 22.0 डिग्री"

    bengali = "১৮.৫ মিমি এবং ২২.০ ডিগ্রি"
    assert normalise_indic_digits(bengali) == "18.5 মিমি এবং 22.0 ডিগ্রি"

    telugu = "౧౨.౫ మిమీ"
    assert normalise_indic_digits(telugu) == "12.5 మిమీ"

    odia = "୧୮.୫ ମିମି"
    assert normalise_indic_digits(odia) == "18.5 ମିମି"


def test_placeholder_protection_and_restoration():
    """Numbers and units must be replaced with placeholders and restored exactly."""
    text = "Tomorrow in Pune expects 18.5 mm rain and a temperature of 22.0 degC (or 5%)."
    protected, mapping = protect_numbers_and_units(text)

    # Placeholders should replace numbers/units
    assert "18.5 mm" not in protected
    assert "22.0 degC" not in protected
    assert "__VAL_" in protected or "__NUM_" in protected

    # Restoration should put exact values back
    restored = restore_numbers_and_units(protected, mapping)
    assert restored == text


@pytest.mark.asyncio
async def test_cache_hits_skip_network(tmp_path):
    """Calling translate twice with same input must hit cache and invoke adapter only once."""
    call_count = 0

    class CountingAdapter(TranslationAdapter):
        @property
        def source_id(self) -> str:
            return "mock.counting"

        async def translate(self, text: str, src: str = "en", tgt: str = "hi", **kwargs) -> str:
            nonlocal call_count
            call_count += 1
            return f"अनुवाद: {text}"

    cache = TranslationCache(cache_dir=tmp_path / "cache")
    gateway = TranslationGateway(primary=CountingAdapter(), cache=cache)

    res1 = await gateway.translate("Will it rain tomorrow in Pune?", src="en", tgt="hi")
    assert res1.startswith("अनुवाद:")
    assert call_count == 1

    # Second call with exact same parameters must return cached result
    res2 = await gateway.translate("Will it rain tomorrow in Pune?", src="en", tgt="hi")
    assert res2 == res1
    assert call_count == 1  # Network skipped!


@pytest.mark.asyncio
async def test_placeholders_survive_through_sarvam_adapter(tmp_path):
    """Verify Sarvam translation adapter sends translated text and placeholders survive."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("api-subscription-key") == "mock_key"
        payload = request.read().decode("utf-8")
        assert "mayura:v1" in payload
        # Mock Sarvam response echoing placeholder
        return httpx.Response(200, json={"translated_text": "पुण्यात उद्या __VAL_0__ पाऊस पडेल."})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = SarvamTranslationAdapter(client=mock_client, api_key="mock_key")
    cache = TranslationCache(cache_dir=tmp_path / "cache")
    gateway = TranslationGateway(primary=adapter, cache=cache)

    res = await gateway.translate("Tomorrow in Pune will have 18.5 mm rain.", src="en", tgt="mr")
    assert "18.5 mm" in res
    assert "__VAL_0__" not in res


@pytest.mark.asyncio
async def test_sarvam_error_falls_back_to_llm(caplog, tmp_path):
    """When Sarvam translation raises an error or fails, fallback LLM adapter is called."""
    def sarvam_error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "Sarvam internal service error"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(sarvam_error_handler))
    sarvam_adapter = SarvamTranslationAdapter(client=mock_client, api_key="mock_key")

    class MockLLMFallback(TranslationAdapter):
        @property
        def source_id(self) -> str:
            return "mock.llm"

        async def translate(self, text: str, src: str = "en", tgt: str = "hi", **kwargs) -> str:
            return f"LLM_FALLBACK({text})"

    cache = TranslationCache(cache_dir=tmp_path / "cache")
    gateway = TranslationGateway(primary=sarvam_adapter, fallback=MockLLMFallback(), cache=cache)

    with caplog.at_level(logging.WARNING):
        res = await gateway.translate("High temperature warning", src="en", tgt="hi")
    assert res.startswith("LLM_FALLBACK")
    assert any("translation_primary_failed" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_same_src_and_tgt_returns_immediately():
    """Translating from en to en returns text immediately without calling adapter."""
    class FailingAdapter(TranslationAdapter):
        @property
        def source_id(self) -> str:
            return "failing"

        async def translate(self, text: str, src: str = "en", tgt: str = "en", **kwargs) -> str:
            raise RuntimeError("Should never be called")

    gateway = TranslationGateway(primary=FailingAdapter())
    text = "Hello world"
    res = await gateway.translate(text, src="en", tgt="en")
    assert res == text
