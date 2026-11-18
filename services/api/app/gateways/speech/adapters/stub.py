from __future__ import annotations

import io
import wave
from typing import Any


class StubSpeechAdapter:
    def __init__(self) -> None:
        pass

    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, Any]:
        return {
            "text": "कल पुणे में बारिश होगी क्या?",
            "language": language,
            "confidence": 0.95,
            "provider": "stub",
            "provenance": "fixture-stub",
        }

    async def speak(self, text: str, language: str = "hi", voice: str = "female") -> bytes:
        # Generates a valid 16 kHz 16-bit mono PCM RIFF WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            # 0.5 seconds of silence
            wf.writeframes(b"\x00\x00" * 8000)
        return buf.getvalue()
