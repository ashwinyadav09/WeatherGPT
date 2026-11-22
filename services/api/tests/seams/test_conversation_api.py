from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

from packages.contracts.validator import validate_schema
from services.api.app.main import app


@pytest.mark.asyncio
async def test_conversation_api_stream_seam():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "session_id": "test_session_123",
            "text": "Will it rain tomorrow in Pune?",
            "language": "en",
            "client_tz": "Asia/Kolkata",
            "stream": True,
        }
        resp = await client.post("/v1/chat", json=payload)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        body = resp.text
        lines = [line.strip() for line in body.splitlines() if line.strip()]

        events = []
        current_event = None
        for line in lines:
            if line.startswith("event: "):
                current_event = line.replace("event: ", "").strip()
            elif line.startswith("data: ") and current_event:
                data = json.loads(line.replace("data: ", "").strip())
                events.append((current_event, data))
                current_event = None

        assert len(events) >= 4  # meta, evidence, tokens/card, done

        # Check meta event
        meta_events = [e for e in events if e[0] == "meta"]
        assert len(meta_events) == 1
        assert "answer_id" in meta_events[0][1]

        # Check evidence event and validate against JSON schema
        evidence_events = [e for e in events if e[0] == "evidence"]
        assert len(evidence_events) >= 1
        evidence_packet = evidence_events[0][1]
        validate_schema("evidence_packet", evidence_packet)
        assert evidence_packet["authority_tier"] in range(1, 6)

        # Check card event
        card_events = [e for e in events if e[0] == "card"]
        assert len(card_events) == 1
        assert "headline" in card_events[0][1]

        # Check trace event and validate against JSON schema (Ticket R2.4)
        trace_events = [e for e in events if e[0] == "trace"]
        assert len(trace_events) == 1
        trace_data = trace_events[0][1]
        validate_schema("trace_event", trace_data)
        assert "intent" in trace_data
        assert "router_path" in trace_data
        assert "tools" in trace_data
        assert "models" in trace_data
        assert "verifier" in trace_data
        assert "llm" in trace_data

        # Check done event
        done_events = [e for e in events if e[0] == "done"]
        assert len(done_events) == 1
        assert "latency_ms" in done_events[0][1]


@pytest.mark.asyncio
async def test_conversation_api_hindi_stream_seam():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "session_id": "test_session_hi_1",
            "text": "क्या कल पुणे में बारिश होगी?",
            "language": "auto",
            "client_tz": "Asia/Kolkata",
            "stream": True,
        }
        resp = await client.post("/v1/chat", json=payload)
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
        events = []
        current_event = None
        for line in lines:
            if line.startswith("event: "):
                current_event = line.replace("event: ", "").strip()
            elif line.startswith("data: ") and current_event:
                data = json.loads(line.replace("data: ", "").strip())
                events.append((current_event, data))
                current_event = None

        token_events = [e for e in events if e[0] == "token"]
        answer_text = "".join(e[1]["text"] for e in token_events)

        # Must be in Hindi and contain weather terms
        assert any(term in answer_text for term in ["बारिश", "वर्षा", "पूर्वानुमान", "संभावना"])
        assert "Open-Meteo" in answer_text
        assert "कनेक्ट नहीं" not in answer_text and "not connected" not in answer_text.lower()
        assert "IMD" not in answer_text and "आईएमडी" not in answer_text

        # Check trace event in Hindi query
        trace_events = [e for e in events if e[0] == "trace"]
        assert len(trace_events) == 1
        trace_data = trace_events[0][1]
        validate_schema("trace_event", trace_data)
        assert trace_data["intent"] == "forecast"

