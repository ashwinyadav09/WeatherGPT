from __future__ import annotations

import time
from typing import Any

import structlog

from services.api.app.gateways.speech.exceptions import ProviderNotConfigured
from services.api.app.registry import get_speech_adapter

logger = structlog.get_logger()


class SpeechGateway:
    """Gateway orchestrating speech-to-text (ASR) and text-to-speech (TTS).

    Sarvam is primary per ADR 0012 and ticket R0.5. Fallback is none.
    When SARVAM_API_KEY is missing, raises ProviderNotConfigured.
    Zero canned transcripts are ever returned.
    """

    def __init__(
        self,
        primary_adapter: Any | None = None,
        fallback_adapter: Any | None = None,
    ) -> None:
        self.primary_adapter = primary_adapter or get_speech_adapter()
        self.fallback_adapter = fallback_adapter

    def is_live(self) -> bool:
        if self.primary_adapter and hasattr(self.primary_adapter, "is_configured"):
            return self.primary_adapter.is_configured()
        return False

    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, Any]:
        """Transcribe audio using primary adapter (Sarvam)."""
        t0 = time.perf_counter()

        if not self.primary_adapter:
            raise ProviderNotConfigured("No speech provider configured.")

        try:
            res = await self.primary_adapter.transcribe(audio_bytes, language=language)
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            res["latency_ms"] = dur_ms
            logger.info("speech_transcribe_success", provider="sarvam", latency_ms=dur_ms)
            return res
        except ProviderNotConfigured:
            raise
        except Exception as e:
            logger.warning("speech_primary_failed", error=str(e), language=language)
            if self.fallback_adapter:
                try:
                    res = await self.fallback_adapter.transcribe(audio_bytes, language=language)
                    dur_ms = round((time.perf_counter() - t0) * 1000, 2)
                    res["latency_ms"] = dur_ms
                    return res
                except Exception as fb_err:
                    logger.warning("speech_fallback_failed", error=str(fb_err), language=language)
            raise

    async def speak(self, text: str, language: str = "hi", voice: str = "female") -> bytes:
        """Synthesize text into speech using primary adapter (Sarvam)."""
        t0 = time.perf_counter()

        if not self.primary_adapter:
            raise ProviderNotConfigured("No speech provider configured.")

        try:
            audio = await self.primary_adapter.speak(text, language=language, voice=voice)
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info("speech_tts_success", provider="sarvam", latency_ms=dur_ms)
            return audio
        except ProviderNotConfigured:
            raise
        except Exception as e:
            logger.warning("speech_primary_tts_failed", error=str(e), language=language)
            if self.fallback_adapter:
                try:
                    return await self.fallback_adapter.speak(text, language=language, voice=voice)
                except Exception as fb_err:
                    logger.warning("speech_fallback_tts_failed", error=str(fb_err), language=language)
            raise
