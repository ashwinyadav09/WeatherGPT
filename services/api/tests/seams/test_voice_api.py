from __future__ import annotations

import base64
import io
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from services.api.app.gateways.speech.adapters.sarvam import SarvamSpeechAdapter
from services.api.app.gateways.speech.router import _gateway
from services.api.app.main import app

client = TestClient(app)


def test_voice_health_endpoint(monkeypatch: pytest.MonkeyPatch):
    """Verify GET /v1/voice/health reports live status based on key presence."""
    # 1. No key -> unavailable
    _gateway.primary_adapter = SarvamSpeechAdapter(api_key="")
    resp = client.get("/v1/voice/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unavailable"
    assert data["configured"] is False
    assert data["provider"] == "sarvam"

    # 2. Key present -> ok
    _gateway.primary_adapter = SarvamSpeechAdapter(api_key="test_sarvam_key")
    resp_live = client.get("/v1/voice/health")
    assert resp_live.status_code == 200
    data_live = resp_live.json()
    assert data_live["status"] == "ok"
    assert data_live["configured"] is True


def test_voice_transcribe_and_speak_without_key_returns_503():
    """Verify /v1/voice/* returns 503 and never returns canned text when key is missing."""
    _gateway.primary_adapter = SarvamSpeechAdapter(api_key="")

    dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    files = {"audio": ("test.wav", io.BytesIO(dummy_audio), "audio/wav")}

    res_stt = client.post("/v1/voice/transcribe", files=files, data={"language": "hi"})
    assert res_stt.status_code == 503
    assert "not configured" in res_stt.text.lower()

    res_tts = client.post("/v1/voice/speak", json={"text": "कल पुणे में बारिश", "language": "hi"})
    assert res_tts.status_code == 503
    assert "not configured" in res_tts.text.lower()


def test_voice_transcribe_and_speak_with_mocked_sarvam():
    """Verify POST /v1/voice/transcribe and /speak call Sarvam and return audio/text."""
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        assert request.headers.get("api-subscription-key") == "mock_sarvam_key"
        if "speech-to-text" in url_str:
            return httpx.Response(200, json={"transcript": "कल पुणे में बारिश होगी क्या?", "confidence": 0.98})
        elif "text-to-speech" in url_str:
            fake_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            return httpx.Response(200, json={"audios": [base64.b64encode(fake_wav).decode()]})
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    _gateway.primary_adapter = SarvamSpeechAdapter(client=mock_client, api_key="mock_sarvam_key")

    dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    files = {"audio": ("test.wav", io.BytesIO(dummy_audio), "audio/wav")}

    res_stt = client.post("/v1/voice/transcribe", files=files, data={"language": "hi"})
    assert res_stt.status_code == 200
    res_json = res_stt.json()
    assert res_json["text"] == "कल पुणे में बारिश होगी क्या?"
    assert res_json["language"] == "hi"

    res_tts = client.post("/v1/voice/speak", json={"text": "कल पुणे में 12 मिमी बारिश", "language": "hi"})
    assert res_tts.status_code == 200
    assert res_tts.headers["content-type"] == "audio/wav"
    assert res_tts.content.startswith(b"RIFF")


def test_place_uncertainty_voice_confirmation_flow():
    """Verify ambiguous or uncertain place names prompt for confirmation and resolve on 'हाँ' / 'Yes'."""
    session_id = "test_voice_conf_session_1"

    # Step 1: Ask about ambiguous Bilaspur
    req1 = {
        "session_id": session_id,
        "text": "बिलासपुर में बारिश होगी क्या?",
        "language": "hi",
        "stream": False,
    }
    resp1 = client.post("/v1/chat", json=req1)
    assert resp1.status_code == 200
    lines = resp1.text.strip().split("\n")
    events = []
    for line in lines:
        if line.startswith("event: "):
            events.append(line.replace("event: ", "").strip())
    assert "card" in events

    # Step 2: Confirm with spoken "हाँ" (Yes)
    req2 = {
        "session_id": session_id,
        "text": "हाँ",
        "language": "hi",
        "stream": False,
    }
    resp2 = client.post("/v1/chat", json=req2)
    assert resp2.status_code == 200
    assert "पूर्वानुमान" in resp2.text or "barish" in resp2.text.lower() or "बारिश" in resp2.text


def test_no_raw_audio_persisted_to_disk():
    """Verify DPDP requirement: zero raw audio files are persisted to disk by the voice gateway."""
    initial_files = set(Path(".").glob("**/*.wav"))

    dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    files = {"audio": ("test_ephemeral.wav", io.BytesIO(dummy_audio), "audio/wav")}

    client.post("/v1/voice/transcribe", files=files, data={"language": "hi"})
    client.post("/v1/voice/speak", json={"text": "परीक्षण", "language": "hi"})

    current_files = set(Path(".").glob("**/*.wav"))
    new_files = current_files - initial_files
    assert len(new_files) == 0, f"Found persisted audio files: {new_files}"
