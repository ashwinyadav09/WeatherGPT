"""Unit tests for RecordedHTTPTransport (Ticket R20.3).

Verifies:
1. Replaying by request hash returns real recorded responses.
2. Request hash miss raises KeyError (never falls back or passes silently).
3. Deleting or missing recording file raises FileNotFoundError.
4. Tampered recording file raises ValueError on SHA-256 mismatch.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from eval.harness import RecordedHTTPTransport
from scripts.tasks.record_fixtures import compute_request_hash

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
RECORDINGS_DIR = ROOT / "eval" / "recordings"


def test_recorded_transport_replays_matching_request():
    """Verify that a recorded forecast request is replayed by request hash."""
    transport = RecordedHTTPTransport()
    client = httpx.Client(transport=transport)

    # Request for Delhi forecast
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "current": "temperature_2m,precipitation",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
        "timezone": "Asia/Kolkata",
        "forecast_days": 7,
    }
    resp = client.get(url, params=params)
    assert resp.status_code == 200
    data = resp.json()
    assert "daily" in data
    assert "temperature_2m_max" in data["daily"]


def test_recorded_transport_raises_on_miss():
    """Verify that an unrecorded request raises KeyError immediately (Rule T7, N3)."""
    transport = RecordedHTTPTransport()
    client = httpx.Client(transport=transport)

    unrecorded_url = "https://api.open-meteo.com/v1/forecast"
    unrecorded_params = {"latitude": 0.0, "longitude": 0.0}

    with pytest.raises(KeyError, match="RecordedHTTPTransport miss"):
        client.get(unrecorded_url, params=unrecorded_params)


def test_recorded_transport_raises_when_recording_deleted(tmp_path: Path):
    """Verify that deleting a recording file causes FileNotFoundError instead of silent pass."""
    manifest_data = [
        {
            "url": "https://api.open-meteo.com/v1/test",
            "parameters": {"test": 1},
            "request_hash": compute_request_hash("https://api.open-meteo.com/v1/test", {"test": 1}),
            "status_code": 200,
            "sha256": "fakehash",
            "file": "missing_file.json",
        }
    ]
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    transport = RecordedHTTPTransport(manifest_path=manifest_path, recordings_dir=tmp_path)
    client = httpx.Client(transport=transport)

    with pytest.raises(FileNotFoundError, match="Recording file missing on disk"):
        client.get("https://api.open-meteo.com/v1/test", params={"test": 1})


def test_recorded_transport_raises_on_tampered_content(tmp_path: Path):
    """Verify that a recording with SHA-256 mismatch raises ValueError."""
    fake_file = tmp_path / "tampered.json"
    fake_file.write_bytes(b'{"tampered": true}')

    manifest_data = [
        {
            "url": "https://api.open-meteo.com/v1/test",
            "parameters": {"test": 1},
            "request_hash": compute_request_hash("https://api.open-meteo.com/v1/test", {"test": 1}),
            "status_code": 200,
            "sha256": "expected_different_sha256",
            "file": "tampered.json",
        }
    ]
    manifest_path = tmp_path / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    transport = RecordedHTTPTransport(manifest_path=manifest_path, recordings_dir=tmp_path)
    client = httpx.Client(transport=transport)

    with pytest.raises(ValueError, match="Recording SHA-256 mismatch"):
        client.get("https://api.open-meteo.com/v1/test", params={"test": 1})
