from __future__ import annotations

from typing import Any

from services.api.app.gateways.speech.adapters.stub import StubSpeechAdapter


class SpeechGateway:
    def __init__(self) -> None:
        self.adapter = StubSpeechAdapter()

    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, Any]:
        return await self.adapter.transcribe(audio_bytes, language)

    async def speak(self, text: str, language: str = "hi", voice: str = "female") -> bytes:
        return await self.adapter.speak(text, language, voice)
