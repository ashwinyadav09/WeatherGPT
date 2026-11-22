from __future__ import annotations

import base64
import os
from typing import Any

import httpx
import structlog

from services.api.app.gateways.speech.exceptions import ProviderNotConfigured
from services.api.app.gateways.speech.tts_normalizer import normalize_for_tts

logger = structlog.get_logger()

SARVAM_LANG_MAP = {
    "hi": "hi-IN",
    "bn": "bn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    "or": "od-IN",
    "od": "od-IN",
    "en": "en-IN",
}


class SarvamSpeechAdapter:
    """Sarvam AI speech adapter for Indic speech (Saaras v3 ASR & Bulbul v3 TTS)."""

    def __init__(self, client: httpx.AsyncClient | None = None, api_key: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("SARVAM_API_KEY", "")
        self.base_url = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai")
        self.client = client

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        return self.client or httpx.AsyncClient(timeout=10.0)

    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, Any]:
        """Transcribe speech audio using Sarvam Saaras v3."""
        if not self.api_key:
            raise ProviderNotConfigured("Sarvam API key is not configured. Voice services are unavailable.")

        lang_code = SARVAM_LANG_MAP.get(language, f"{language}-IN" if "-" not in language else language)
        client = await self._get_client()
        headers = {"api-subscription-key": self.api_key}
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {
            "model": "saaras:v3",
            "language_code": lang_code,
        }

        try:
            resp = await client.post(
                f"{self.base_url}/speech-to-text",
                headers=headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()
            res_json = resp.json()
            return {
                "text": res_json.get("transcript", ""),
                "language": language,
                "confidence": res_json.get("confidence", 0.95),
                "provider": "sarvam",
                "provenance": "live",
            }
        finally:
            if not self.client:
                await client.aclose()

    async def speak(self, text: str, language: str = "hi", voice: str = "female") -> bytes:
        """Synthesize natural speech using Sarvam Bulbul v3."""
        if not self.api_key:
            raise ProviderNotConfigured("Sarvam API key is not configured. Voice services are unavailable.")

        natural_text = normalize_for_tts(text, language=language)
        lang_code = SARVAM_LANG_MAP.get(language, f"{language}-IN" if "-" not in language else language)

        client = await self._get_client()
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        speaker = "meera" if voice == "female" else "arvind"
        payload = {
            "inputs": [natural_text],
            "target_language_code": lang_code,
            "speaker": speaker,
            "pitch": 0,
            "pace": 1.0,
            "loudness": 1.5,
            "speech_sample_rate": 16000,
            "enable_preprocessing": True,
            "model": "bulbul:v3",
        }

        try:
            resp = await client.post(
                f"{self.base_url}/text-to-speech",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            res_json = resp.json()
            audios = res_json.get("audios", [])
            if audios:
                return base64.b64decode(audios[0])
            return b""
        finally:
            if not self.client:
                await client.aclose()
