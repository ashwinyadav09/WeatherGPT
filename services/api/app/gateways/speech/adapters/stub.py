from __future__ import annotations


class StubSpeechAdapter:
    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, str | float]:
        return {
            "text": "कल पुणे में बारिश होगी क्या?",
            "language": language,
            "confidence": 0.95,
        }

    async def speak(self, text: str, language: str = "hi", voice: str = "female") -> bytes:
        # Returns empty or dummy audio bytes for stub
        return b"RIFFstubWAVEfmt "
