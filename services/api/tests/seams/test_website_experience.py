from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from services.api.app.licence import get_licence_register
from services.api.app.main import app

ROOT = Path(__file__).resolve().parents[4]
WEB_ROOT = ROOT / "apps" / "web"


def test_pwa_manifest_and_sw_fidelity():
    manifest_path = WEB_ROOT / "public" / "manifest.json"
    sw_path = WEB_ROOT / "public" / "sw.js"
    offline_path = WEB_ROOT / "public" / "offline.html"

    assert manifest_path.exists(), "manifest.json missing"
    assert sw_path.exists(), "sw.js missing"
    assert offline_path.exists(), "offline.html missing"

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["name"] == "WeatherGPT - India Weather Assistant"
    assert manifest["theme_color"] == "#1B7F3B"
    assert manifest["display"] == "standalone"
    assert len(manifest["icons"]) >= 2

    # Verify SW content
    sw_text = sw_path.read_text(encoding="utf-8")
    assert "CACHE_NAME" in sw_text
    assert "stale-while-revalidate" in sw_text or "sw-fetched-at" in sw_text
    assert "SKIP_WAITING" in sw_text
    assert "/offline.html" in sw_text


def test_sources_and_licences_register():
    client = TestClient(app)
    resp = client.get("/v1/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 4

    sources = {item["source_id"]: item for item in data}
    assert "open_meteo.forecast" in sources
    assert "CC BY 4.0" in sources["open_meteo.forecast"]["terms"]
    assert "imd.city_forecast" in sources
    assert "sachet.cap" in sources

    # Direct model verification
    reg = get_licence_register()
    assert len(reg) >= 4


def test_dpdp_privacy_consent_and_delete_data():
    client = TestClient(app)

    # English Notice
    resp_en = client.get("/v1/privacy/consent?lang=en")
    assert resp_en.status_code == 200
    en_data = resp_en.json()
    assert "DPDP" in en_data["title"]
    assert len(en_data["items"]) >= 2
    assert any(i["purpose"] == "location" for i in en_data["items"])
    assert any(i["purpose"] == "voice" for i in en_data["items"])

    # Hindi Notice
    resp_hi = client.get("/v1/privacy/consent?lang=hi")
    assert resp_hi.status_code == 200
    hi_data = resp_hi.json()
    assert "गोपनीयता" in hi_data["title"]
    assert any(i["purpose"] == "location" for i in hi_data["items"])

    # Delete my data endpoint
    resp_del = client.post("/v1/privacy/delete-data", json={"session_id": "test_session_123"})
    assert resp_del.status_code == 200
    del_data = resp_del.json()
    assert del_data["deleted"] is True
    assert "audit_reference" in del_data
    assert del_data["session_id"] == "test_session_123"
