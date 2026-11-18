from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

from services.api.app.main import app

client = TestClient(app)


def test_voice_transcribe_endpoint():
    """Verify POST /v1/voice/transcribe accepts audio file and returns transcription."""
    # 16-sample minimal WAV
    dummy_audio = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"

    files = {"audio": ("test.wav", io.BytesIO(dummy_audio), "audio/wav")}
    data = {"language": "hi"}

    response = client.post("/v1/voice/transcribe", files=files, data=data)
    assert response.status_code == 200
    res_json = response.json()
    assert "text" in res_json
    assert res_json["language"] == "hi"
    assert "confidence" in res_json


def test_voice_speak_endpoint():
    """Verify POST /v1/voice/speak returns standard WAV audio stream."""
    req_body = {
        "text": "कल पुणे में 12 मिमी बारिश और 28 डिग्री तापमान रहेगा।",
        "language": "hi",
        "voice": "female",
    }
    response = client.post("/v1/voice/speak", json=req_body)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content.startswith(b"RIFF")
    assert b"WAVE" in response.content


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
