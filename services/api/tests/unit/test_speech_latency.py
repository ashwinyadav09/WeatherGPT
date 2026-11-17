from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from services.api.app.gateways.speech.gateway import SpeechGateway


class Simulated4GAdapter:
    """Simulates 4G network latency (typical mobile network RTT + inference time)."""

    def __init__(self, asr_delay_s: float = 0.05, tts_delay_s: float = 0.05) -> None:
        self.asr_delay_s = asr_delay_s
        self.tts_delay_s = tts_delay_s

    async def transcribe(self, audio_bytes: bytes, language: str = "hi") -> dict[str, Any]:
        await asyncio.sleep(self.asr_delay_s)
        return {
            "text": "कल पुणे में बारिश होगी क्या?",
            "language": language,
            "confidence": 0.95,
            "provider": "simulated_4g",
        }

    async def speak(self, text: str, language: str = "hi", voice: str = "female") -> bytes:
        await asyncio.sleep(self.tts_delay_s)
        # Returns standard RIFF WAV
        return b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


@pytest.mark.asyncio
async def test_first_audio_arrives_within_3_5s_p95():
    """Verify first audio arrives within 3.5 seconds at p95 under simulated 4G conditions."""
    gateway = SpeechGateway(primary_adapter=Simulated4GAdapter())
    dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    latencies_ms: list[float] = []

    # Run 10 instrumented voice turns
    for _ in range(10):
        t0 = time.perf_counter()

        # Step 1: ASR
        transcription = await gateway.transcribe(dummy_audio, language="hi")
        assert transcription["text"]

        # Step 2: TTS (first audio generation)
        audio = await gateway.speak(transcription["text"], language="hi")
        assert len(audio) > 0

        turn_duration_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(turn_duration_ms)

    latencies_ms.sort()
    p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]

    # Assert p95 is strictly under 3.5 seconds (3500 ms)
    assert p95 <= 3500.0, f"p95 latency was {p95:.1f} ms, exceeded 3500 ms budget"
    assert p50 <= 2000.0, f"p50 latency was {p50:.1f} ms"
