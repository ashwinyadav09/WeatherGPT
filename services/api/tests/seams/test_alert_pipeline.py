from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from packages.contracts.validator import validate_schema
from services.api.app.evidence.models import AlertModel
from services.api.app.main import app
from services.api.app.modules.alerts.engine import (
    AlertEngine,
    point_in_polygon,
    render_alert_template,
)
from services.api.app.modules.alerts.router import _engine

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
FIXTURE_PATH = ROOT / "eval" / "fixtures" / "sachet" / "alert_sample.json"


@pytest.mark.asyncio
async def test_alert_pipeline_seam():
    assert FIXTURE_PATH.exists(), f"Fixture missing at {FIXTURE_PATH}"
    with FIXTURE_PATH.open("r", encoding="utf-8") as f:
        fixture_data = json.load(f)

    # Clean fixture metadata before schema validation
    alert_clean = {k: v for k, v in fixture_data.items() if not k.startswith("_")}
    validate_schema("alert", alert_clean)

    # Ingest alert into engine
    alert_model = AlertModel(**alert_clean)
    _engine.ingest_sample_alert(alert_model)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        assert isinstance(alerts, list)
        assert len(alerts) >= 1

        first = alerts[0]
        validate_schema("alert", first)
        assert first["severity"] in ["Extreme", "Severe", "Moderate", "Minor", "Unknown"]
        assert first["level"] in ["green", "yellow", "orange", "red"]
        assert first["authority_tier"] == 1

        # Test Web Push subscription lifecycle
        sub_payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/sample-token-123",
            "keys": {"p256dh": "dummy-p256dh", "auth": "dummy-auth"},
            "places": ["Pune", "Nashik"],
            "severities": ["Extreme", "Severe"],
            "quiet_hours": {"start": "22:00", "end": "06:00"},
        }
        sub_resp = await client.post("/v1/push/subscribe", json=sub_payload)
        assert sub_resp.status_code == 201
        assert sub_resp.json()["status"] == "subscribed"

        del_resp = await client.delete(
            "/v1/push/subscribe",
            params={"endpoint": "https://fcm.googleapis.com/fcm/send/sample-token-123"},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "unsubscribed"


def test_point_in_polygon_and_border_cases():
    # Triangle: (18.50, 73.80) - (18.60, 73.80) - (18.60, 73.90) - (18.50, 73.80)
    poly = [(18.50, 73.80), (18.60, 73.80), (18.60, 73.90), (18.50, 73.80)]

    # Point clearly inside
    assert point_in_polygon(18.55, 73.82, poly) is True

    # Point clearly outside
    assert point_in_polygon(18.40, 73.80, poly) is False
    assert point_in_polygon(18.55, 73.95, poly) is False

    # Border case: point on the boundary/edge
    assert point_in_polygon(18.55, 73.80, poly) is True
    assert point_in_polygon(18.50, 73.80, poly) is True


def test_engine_polygon_and_district_matching():
    engine = AlertEngine()

    sample_alert = AlertModel(
        id="urn:test:pune:1",
        sender="NDMA",
        sent="2026-11-17T06:00:00Z",
        status="Actual",
        msg_type="Alert",
        hazard="Thunderstorm",
        severity="Moderate",
        urgency="Expected",
        certainty="Likely",
        onset="2026-11-17T06:00:00Z",
        expires="2026-12-31T23:59:59Z",
        areas=[
            {
                "areaDesc": "Pune District",
                "polygon": "18.50,73.80 18.60,73.80 18.60,73.90 18.50,73.80",
            }
        ],
        text_by_language={"en": "Thunderstorm in Pune"},
        source_url="https://sachet.ndma.gov.in/test1",
        authority_tier=1,
        level="yellow",
    )
    engine.ingest_sample_alert(sample_alert)

    # 1. Match by polygon point
    matched = engine.match_alerts(lat=18.55, lon=73.82)
    assert len(matched) == 1
    assert matched[0].id == "urn:test:pune:1"

    # Outside polygon, no district match
    unmatched = engine.match_alerts(lat=28.61, lon=77.20)
    assert len(unmatched) == 0

    # 2. Match by district fallback
    district_matched = engine.match_alerts(lat=0.0, lon=0.0, district="Pune")
    assert len(district_matched) == 1


def test_update_and_cancel_lifecycle():
    engine = AlertEngine()

    # Initial Alert
    alert_1 = AlertModel(
        id="urn:test:alert:001",
        sender="NDMA",
        sent="2026-11-17T06:00:00Z",
        status="Actual",
        msg_type="Alert",
        hazard="Heavy Rain",
        severity="Moderate",
        urgency="Expected",
        certainty="Likely",
        onset="2026-11-17T06:00:00Z",
        expires="2026-12-31T23:59:59Z",
        areas=[{"areaDesc": "Nashik District", "polygon": ""}],
        text_by_language={"en": "Heavy rain expected"},
        source_url="https://sachet.ndma.gov.in/001",
        authority_tier=1,
        level="yellow",
    )
    engine.ingest_sample_alert(alert_1)
    active = engine.get_all_active()
    assert len(active) == 1
    assert active[0].severity == "Moderate"

    # Update Alert (escalate to Severe)
    alert_update = AlertModel(
        id="urn:test:alert:002",
        sender="NDMA",
        sent="2026-11-17T08:00:00Z",
        status="Actual",
        msg_type="Update",
        hazard="Very Heavy Rain",
        severity="Severe",
        urgency="Expected",
        certainty="Likely",
        onset="2026-11-17T08:00:00Z",
        expires="2026-12-31T23:59:59Z",
        areas=[{"areaDesc": "Nashik District", "polygon": ""}],
        text_by_language={"en": "Very heavy rain expected"},
        source_url="https://sachet.ndma.gov.in/002",
        authority_tier=1,
        level="orange",
    )
    # References original alert
    engine.ingest_sample_alert(alert_update, references="urn:test:alert:001")
    active = engine.get_all_active()
    assert len(active) == 1
    assert active[0].id == "urn:test:alert:002"
    assert active[0].severity == "Severe"

    # Cancel Alert
    alert_cancel = AlertModel(
        id="urn:test:alert:003",
        sender="NDMA",
        sent="2026-11-17T10:00:00Z",
        status="Actual",
        msg_type="Cancel",
        hazard="Rain",
        severity="Minor",
        urgency="Past",
        certainty="Observed",
        onset="2026-11-17T10:00:00Z",
        expires="2026-12-31T23:59:59Z",
        areas=[{"areaDesc": "Nashik District", "polygon": ""}],
        text_by_language={"en": "All clear"},
        source_url="https://sachet.ndma.gov.in/003",
        authority_tier=1,
        level="green",
    )
    engine.ingest_sample_alert(alert_cancel, references="urn:test:alert:002")
    active = engine.get_all_active()
    assert len(active) == 0


def test_template_rendering_en_and_hi():
    alert = AlertModel(
        id="urn:test:tmpl:1",
        sender="IMD",
        sent="2026-11-17T06:00:00Z",
        status="Actual",
        msg_type="Alert",
        hazard="Thunderstorm",
        severity="Severe",
        urgency="Expected",
        certainty="Likely",
        onset="2026-11-17T08:00:00Z",
        expires="2026-11-17T12:00:00Z",
        areas=[{"areaDesc": "Pune", "polygon": ""}],
        text_by_language={},
        source_url="https://sachet.ndma.gov.in/tmpl1",
        authority_tier=1,
        level="orange",
    )

    rendered_en = render_alert_template(alert, place_name="Pune", lang="en")
    assert "orange alert: thunderstorm in pune" in rendered_en["headline"].lower()
    assert "Be prepared." in rendered_en["meaning"]

    rendered_hi = render_alert_template(alert, place_name="पुणे", lang="hi")
    assert "अलर्ट" in rendered_hi["headline"]
    assert "तैयार रहें।" in rendered_hi["meaning"]


def test_replay_latency_p95_under_60s():
    """Replay at least 10 real recorded alerts and measure processing latency."""
    engine = AlertEngine()
    sachet_dir = ROOT / "eval" / "fixtures" / "sachet"
    json_files = sorted(sachet_dir.glob("sachet_*.json"))[:15]
    assert len(json_files) >= 10, "At least 10 fixtures required for latency check"

    latencies_ms = []
    for f in json_files:
        with f.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        clean = {k: v for k, v in data.items() if not k.startswith("_")}
        alert = AlertModel(**clean)

        t0 = time.perf_counter()
        engine.ingest_sample_alert(alert)
        _matched = engine.match_alerts(lat=18.52, lon=73.85, district="Pune")
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)

    latencies_ms.sort()
    p95_ms = latencies_ms[int(0.95 * len(latencies_ms))]

    # p95 must be well under 60,000 ms (60 seconds)
    assert p95_ms < 60000.0
    print(f"\nReplay p95 latency: {p95_ms:.2f} ms")
