from __future__ import annotations

import time
from typing import Any

import structlog

from services.api.app.gateways.speech.adapters.bhashini import BhashiniSpeechAdapter
from services.api.app.gateways.speech.adapters.sarvam import SarvamSpeechAdapter
from services.api.app.gateways.speech.adapters.stub import StubSpeechAdapter

logger = structlog.get_logger()


class SpeechGateway:
    """Gateway orchestrating speech-to-text (ASR) and text-to-speech (TTS) across providers with fallback."""

    def __init__(
        self,
        primary_adapter: Any | None = None,
        fallback_adapter: Any | None = None,
    ) -> None:
        self.primary_adapter = primary_adapter or BhashiniSpeechAdapter()
        self.fallback_adapter = fallback_adapter or SarvamSpeechAdapter()
        self.stub_adapter = StubSpeechAdapter()

    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, Any]:
        """Transcribe audio with primary adapter, falling back on error."""
        t0 = time.perf_counter()
        errors = []

        # Try primary adapter (Bhashini)
        try:
            res = await self.primary_adapter.transcribe(audio_bytes, language=language)
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            res["latency_ms"] = dur_ms
            logger.info("speech_transcribe_success", provider="primary", latency_ms=dur_ms)
            return res
        except Exception as e:
            errors.append(f"primary: {e}")
            logger.warning("speech_primary_failed", error=str(e), language=language)

        # Fall back to second provider (Sarvam)
        try:
            res = await self.fallback_adapter.transcribe(audio_bytes, language=language)
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            res["latency_ms"] = dur_ms
            logger.info("speech_transcribe_fallback_success", provider="fallback", latency_ms=dur_ms)
            return res
        except Exception as e:
            errors.append(f"fallback: {e}")
            logger.warning("speech_fallback_failed", error=str(e), language=language)

        # Ultimate fallback to deterministic stub
        res = await self.stub_adapter.transcribe(audio_bytes, language=language)
        res["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        res["warning"] = f"Speech providers failed ({'; '.join(errors)}); used stub"
        return res

    async def speak(self, text: str, language: str = "hi", voice: str = "female") -> bytes:
        """Synthesize text into speech with primary adapter, falling back on error."""
        t0 = time.perf_counter()

        # Try primary adapter
        try:
            audio = await self.primary_adapter.speak(text, language=language, voice=voice)
            if audio and len(audio) > 44:  # At least larger than a bare header
                dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                logger.info("speech_tts_success", provider="primary", latency_ms=dur_ms)
                return audio
        except Exception as e:
            logger.warning("speech_primary_tts_failed", error=str(e), language=language)

        # Fall back to second provider
        try:
            audio = await self.fallback_adapter.speak(text, language=language, voice=voice)
            if audio and len(audio) > 44:
                dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                logger.info("speech_tts_fallback_success", provider="fallback", latency_ms=dur_ms)
                return audio
        except Exception as e:
            logger.warning("speech_fallback_tts_failed", error=str(e), language=language)

        # Fallback to stub
        return await self.stub_adapter.speak(text, language=language, voice=voice)
