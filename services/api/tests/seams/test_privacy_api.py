from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.app.main import app


@pytest.mark.asyncio
async def test_privacy_consent_notices():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. English consent notice
        resp_en = await client.get("/v1/privacy/consent?lang=en")
        assert resp_en.status_code == 200
        data_en = resp_en.json()
        assert "items" in data_en
        assert any(item["purpose"] == "location" for item in data_en["items"])
        assert "grievance_contact" in data_en

        # 2. Hindi consent notice
        resp_hi = await client.get("/v1/privacy/consent?lang=hi")
        assert resp_hi.status_code == 200
        data_hi = resp_hi.json()
        assert "items" in data_hi
        assert any("स्थान" in item["title"] or "स्थान" in item["description"] for item in data_hi["items"])


@pytest.mark.asyncio
async def test_privacy_delete_my_data():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/v1/privacy/delete-data",
            json={"session_id": "session_to_delete_123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True
        assert "audit_reference" in data
