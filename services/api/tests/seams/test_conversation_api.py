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

        # Check done event
        done_events = [e for e in events if e[0] == "done"]
        assert len(done_events) == 1
        assert "latency_ms" in done_events[0][1]
