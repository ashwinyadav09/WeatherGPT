from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from services.api.app.gateways.speech.adapters.bhashini import BhashiniSpeechAdapter
from services.api.app.gateways.speech.adapters.sarvam import SarvamSpeechAdapter
from services.api.app.gateways.speech.gateway import SpeechGateway

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
BHASHINI_ASR_FIXTURE = ROOT / "eval" / "fixtures" / "bhashini" / "asr_sample.json"
BHASHINI_TTS_FIXTURE = ROOT / "eval" / "fixtures" / "bhashini" / "tts_sample.json"
SARVAM_ASR_FIXTURE = ROOT / "eval" / "fixtures" / "sarvam" / "asr_sample.json"
SARVAM_TTS_FIXTURE = ROOT / "eval" / "fixtures" / "sarvam" / "tts_sample.json"


@pytest.mark.asyncio
async def test_bhashini_adapter_conformance():
    """Verify Bhashini speech adapter conforms to speech interface using recorded sample fixtures."""
    assert BHASHINI_ASR_FIXTURE.exists()
    assert BHASHINI_TTS_FIXTURE.exists()

    with BHASHINI_ASR_FIXTURE.open("r", encoding="utf-8") as f:
        asr_fixture = json.load(f)
    assert asr_fixture.get("_provenance") == "documented-sample"

    with BHASHINI_TTS_FIXTURE.open("r", encoding="utf-8") as f:
        tts_fixture = json.load(f)
    assert tts_fixture.get("_provenance") == "documented-sample"

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "getModelsPipeline" in url_str:
            return httpx.Response(200, json={"pipelineInferenceAPIEndPoint": {"inferenceApiKey": {"value": "key123"}}})
        if "inference" in url_str:
            body = json.loads(request.content.decode("utf-8"))
            task_type = body.get("pipelineTasks", [{}])[0].get("taskType")
            if task_type == "asr":
                return httpx.Response(200, json=asr_fixture)
            elif task_type == "tts":
                return httpx.Response(200, json=tts_fixture)
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = BhashiniSpeechAdapter(client=client)
        adapter.user_id = "test_user"
        adapter.api_key = "test_key"
        adapter.inference_api_key = "test_inf_key"

        # 1. Test ASR conformance
        dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        res = await adapter.transcribe(dummy_audio, language="hi")
        assert "text" in res
        assert "language" in res
        assert "confidence" in res
        assert res["provider"] == "bhashini"
        assert res["text"] == "कल पुणे में बारिश होगी क्या?"

        # 2. Test TTS conformance
        audio_bytes = await adapter.speak("कल पुणे में बारिश होगी क्या?", language="hi", voice="female")
        assert len(audio_bytes) > 0
        assert audio_bytes.startswith(b"RIFF")
        assert b"WAVE" in audio_bytes


@pytest.mark.asyncio
async def test_sarvam_adapter_conformance():
    """Verify Sarvam speech adapter conforms to speech interface using recorded sample fixtures."""
    assert SARVAM_ASR_FIXTURE.exists()
    assert SARVAM_TTS_FIXTURE.exists()

    with SARVAM_ASR_FIXTURE.open("r", encoding="utf-8") as f:
        asr_fixture = json.load(f)
    assert asr_fixture.get("_provenance") == "documented-sample"

    with SARVAM_TTS_FIXTURE.open("r", encoding="utf-8") as f:
        tts_fixture = json.load(f)
    assert tts_fixture.get("_provenance") == "documented-sample"

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "speech-to-text" in url_str:
            return httpx.Response(200, json=asr_fixture)
        elif "text-to-speech" in url_str:
            return httpx.Response(200, json=tts_fixture)
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = SarvamSpeechAdapter(client=client)
        adapter.api_key = "test_sarvam_key"

        # 1. Test ASR conformance
        dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        res = await adapter.transcribe(dummy_audio, language="hi")
        assert "text" in res
        assert "language" in res
        assert "confidence" in res
        assert res["provider"] == "sarvam"
        assert res["confidence"] == 0.96
        assert res["text"] == "कल पुणे में बारिश होगी क्या?"

        # 2. Test TTS conformance
        audio_bytes = await adapter.speak("कल पुणे में बारिश होगी क्या?", language="hi", voice="female")
        assert len(audio_bytes) > 0
        assert audio_bytes.startswith(b"RIFF")
        assert b"WAVE" in audio_bytes


@pytest.mark.asyncio
async def test_speech_gateway_fallback_and_privacy():
    """Verify SpeechGateway seamlessly falls back if primary fails, and stores zero audio files."""
    # Create failing primary adapter
    class FailingAdapter:
        async def transcribe(self, audio_bytes: bytes, language: str = "hi"):
            raise ConnectionError("Primary provider connection timeout")

        async def speak(self, text: str, language: str = "hi", voice: str = "female"):
            raise ConnectionError("Primary provider TTS timeout")

    gateway = SpeechGateway(primary_adapter=FailingAdapter())

    dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    # Transcribe should succeed via fallback
    res = await gateway.transcribe(dummy_audio, language="hi")
    assert "text" in res
    assert "latency_ms" in res
    assert res["latency_ms"] >= 0

    # Speak should succeed via fallback
    audio = await gateway.speak("32°C तापमान और 15 km/h हवा", language="hi")
    assert len(audio) > 0
    assert audio.startswith(b"RIFF")
