from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from packages.contracts.validator import validate_schema
from services.api.app.evidence.models import AlertModel
from services.api.app.main import app
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
