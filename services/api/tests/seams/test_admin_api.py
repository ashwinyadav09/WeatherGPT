from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.app.main import app

ADMIN_HEADER = {"X-Admin-Token": "test-admin-secret-token"}


@pytest.mark.asyncio
async def test_admin_auth_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. No token
        resp = await client.get("/v1/admin/glossary/hi")
        assert resp.status_code in (401, 403)

        # 2. Invalid token
        resp = await client.get(
            "/v1/admin/glossary/hi",
            headers={"X-Admin-Token": "wrong-token"},
        )
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_admin_glossary_update_and_audit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Get glossary
        resp = await client.get("/v1/admin/glossary/hi", headers=ADMIN_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert "terms" in data

        # Update glossary
        update_payload = {
            "editor": "ashwin",
            "terms": {"rain": "बरसात", "forecast": "पूर्वानुमान"},
        }
        post_resp = await client.post(
            "/v1/admin/glossary/hi",
            headers=ADMIN_HEADER,
            json=update_payload,
        )
        assert post_resp.status_code == 200
        post_data = post_resp.json()
        assert post_data["success"] is True
        assert post_data["version"] >= 1

        # Check audit log
        audit_resp = await client.get("/v1/admin/audit", headers=ADMIN_HEADER)
        assert audit_resp.status_code == 200
        audit_data = audit_resp.json()
        assert len(audit_data["entries"]) >= 1
        latest = audit_data["entries"][-1]
        assert latest["who"] == "ashwin"
        assert latest["what"] == "update_glossary"


@pytest.mark.asyncio
async def test_admin_template_requires_reviewer_signoff():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Template update without reviewer must fail
        invalid_payload = {
            "editor": "ashwin",
            "hazard": "rain",
            "severity": "orange",
            "template_text": "भारी बारिश की चेतावनी।",
            # missing reviewer
        }
        resp = await client.post(
            "/v1/admin/templates/hi",
            headers=ADMIN_HEADER,
            json=invalid_payload,
        )
        assert resp.status_code in (400, 422)

        # Template update with reviewer must succeed
        valid_payload = {
            "editor": "ashwin",
            "reviewer": "Pradeep Chhaba",
            "hazard": "rain",
            "severity": "orange",
            "template_text": "कल भारी बारिश की चेतावनी जारी की गई है।",
        }
        resp2 = await client.post(
            "/v1/admin/templates/hi",
            headers=ADMIN_HEADER,
            json=valid_payload,
        )
        assert resp2.status_code == 200
        assert resp2.json()["success"] is True
        assert resp2.json()["reviewer"] == "Pradeep Chhaba"


@pytest.mark.asyncio
async def test_admin_rollback():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Rollback glossary
        rollback_payload = {
            "editor": "ashwin",
            "target": "glossary",
            "language": "hi",
            "target_version": 1,
        }
        resp = await client.post(
            "/v1/admin/rollback",
            headers=ADMIN_HEADER,
            json=rollback_payload,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


@pytest.mark.asyncio
async def test_admin_glossary_changes_take_effect_without_restart():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Update glossary: change rain word to "बरसात"
        update_resp = await client.post(
            "/v1/admin/glossary/hi",
            headers=ADMIN_HEADER,
            json={"editor": "ashwin", "terms": {"rain": "बरसात"}},
        )
        assert update_resp.status_code == 200

        # Query chat in Hindi
        payload = {
            "session_id": "test_session_admin_change",
            "text": "क्या कल पुणे में बारिश होगी?",
            "language": "hi",
            "client_tz": "Asia/Kolkata",
            "stream": True,
        }
        resp = await client.post("/v1/chat", json=payload)
        assert resp.status_code == 200
        assert "बरसात" in resp.text


@pytest.mark.asyncio
async def test_admin_language_quality_dashboard():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/admin/languages", headers=ADMIN_HEADER)
        assert resp.status_code == 200
        data = resp.json()
        assert "languages" in data
        codes = [item["code"] for item in data["languages"]]
        for code in ["en", "hi", "bn", "mr", "te", "ta"]:
            assert code in codes

