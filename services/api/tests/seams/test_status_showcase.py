"""Seam tests for real-time integration showcase and status dashboard (Ticket 08)."""
from __future__ import annotations

import datetime as dt

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.app.main import app
from services.api.app.modules.status.service import StatusTracker
from services.ingest.wis2_subscriber import WIS2Subscriber


@pytest.mark.asyncio
async def test_status_endpoint_structure_and_freshness_targets():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/status")
        assert resp.status_code == 200
        data = resp.json()

        assert "sources" in data
        assert "freshness_targets" in data
        assert "alert_latency" in data
        assert "model_cycles" in data
        assert "wis2_subscriber" in data

        # Check freshness targets visible
        targets = data["freshness_targets"]
        assert targets["imd_warnings_max_seconds"] == 300  # 5 minutes
        assert targets["model_fields_max_seconds"] == 1800  # 30 minutes


def test_wis2_subscriber_message_handling_and_uptime():
    subscriber = WIS2Subscriber(broker_host="globalbroker.meteo.fr")
    # WIS2Subscriber is NOT ENABLED; _connected starts False until a real MQTT handshake.
    assert subscriber.is_connected() is False

    # Ingest a standard WIS2 notification message for India
    sample_wis2 = {
        "id": "urn:wmo:wis2:in-imd:data:core:weather:surface-based-observations:synop:20261117",
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [77.20, 28.61]},
        "properties": {
            "data_id": "wis2/in-imd/synop/VIDP/20261117120000",
            "pubtime": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "links": [{"rel": "canonical", "href": "https://wis2.imd.gov.in/data/synop/VIDP.bufr"}],
    }
    msg = subscriber.process_message("origin/a/wis2/in-imd/data/core/weather/surface-based-observations/synop", sample_wis2)
    assert msg.topic.startswith("origin/a/wis2/in-imd")
    assert subscriber.messages_received_count >= 1

    uptime_report = subscriber.get_uptime_report()
    # uptime_pct is NOT MEASURED (subscriber is not enabled; no live connection).
    assert uptime_report["uptime_pct"] == "NOT MEASURED"
    # status reflects the real connection state
    assert uptime_report["status"] == "disconnected"


def test_injected_delays_reflected_on_dashboard():
    tracker = StatusTracker()
    tracker.record_heartbeat("open_meteo", latency_sec=0.2)
    tracker.record_heartbeat("sachet", latency_sec=0.5)

    # Ingest normal check
    report = tracker.get_status_report()
    assert report["sources"]["open_meteo"]["delay_injected"] is False

    # Inject delay for SACHET
    tracker.inject_delay("sachet", delay_sec=420.0)  # 7 minute delay (exceeds 5 min target)
    delayed_report = tracker.get_status_report()

    assert delayed_report["sources"]["sachet"]["delay_injected"] is True
    assert delayed_report["sources"]["sachet"]["effective_lag_sec"] >= 420.0
    assert delayed_report["sources"]["sachet"]["target_breached"] is True


def test_model_cycle_ingest_completeness():
    tracker = StatusTracker()
    tracker.record_model_cycle(
        model="gfs",
        cycle_time="2026-11-17T00:00:00Z",
        expected_steps=20,
        received_steps=20,
    )
    tracker.record_model_cycle(
        model="ecmwf_ifs",
        cycle_time="2026-11-17T00:00:00Z",
        expected_steps=40,
        received_steps=38,  # incomplete run
    )

    report = tracker.get_status_report()
    cycles = report["model_cycles"]
    assert len(cycles) >= 2

    gfs = next(c for c in cycles if c["model"] == "gfs")
    assert gfs["completeness_pct"] == 100.0
    assert gfs["is_complete"] is True

    ecmwf = next(c for c in cycles if c["model"] == "ecmwf_ifs")
    assert ecmwf["completeness_pct"] == 95.0
    assert ecmwf["is_complete"] is False
