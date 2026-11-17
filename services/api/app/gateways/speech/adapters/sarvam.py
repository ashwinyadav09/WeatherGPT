from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import httpx
import structlog

from services.api.app.gateways.speech.tts_normalizer import normalize_for_tts

logger = structlog.get_logger()

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
ASR_FIXTURE_PATH = ROOT / "eval" / "fixtures" / "sarvam" / "asr_sample.json"
TTS_FIXTURE_PATH = ROOT / "eval" / "fixtures" / "sarvam" / "tts_sample.json"


class SarvamSpeechAdapter:
    """Sarvam AI speech adapter for Indic speech (Saaras v3 ASR & Bulbul v3 TTS)."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        self.base_url = os.getenv("SARVAM_BASE_URL", "https://api.sarvam.ai")
        self.client = client

    async def _get_client(self) -> httpx.AsyncClient:
        return self.client or httpx.AsyncClient(timeout=10.0)

    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, Any]:
        """Transcribe speech audio using Sarvam Saaras v3."""
        if not self.api_key:
            # Documented fixture mode for offline / test runs
            if ASR_FIXTURE_PATH.exists():
                with ASR_FIXTURE_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        "text": data.get("transcript", "कल पुणे में बारिश होगी क्या?"),
                        "language": language,
                        "confidence": data.get("confidence", 0.96),
                        "provider": "sarvam",
                        "provenance": data.get("_provenance", "documented-sample"),
                    }
            return {
                "text": "कल पुणे में बारिश होगी क्या?",
                "language": language,
                "confidence": 0.96,
                "provider": "sarvam",
                "provenance": "stub",
            }

        client = await self._get_client()
        headers = {"api-subscription-key": self.api_key}
        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data = {
            "model": "saaras:v3",
            "language_code": f"{language}-IN" if "-" not in language else language,
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
        natural_text = normalize_for_tts(text, language=language)

        if not self.api_key:
            if TTS_FIXTURE_PATH.exists():
                with TTS_FIXTURE_PATH.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    audios = data.get("audios", [])
                    if audios:
                        return base64.b64decode(audios[0])
            return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

        client = await self._get_client()
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        speaker = "meera" if voice == "female" else "arvind"
        payload = {
            "inputs": [natural_text],
            "target_language_code": f"{language}-IN" if "-" not in language else language,
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
