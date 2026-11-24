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


def test_tier1_locales_and_indic_fonts():
    """Verify all seven Tier-1 locales exist with required UI keys and Indic fonts configured (Ticket R17)."""
    locales_dir = WEB_ROOT / "src" / "i18n" / "locales"
    tier1_codes = ["en", "hi", "bn", "mr", "te", "ta", "or"]

    required_keys = ["app_name", "ask", "ml_lab", "why_this_answer", "source", "official_alert"]

    for code in tier1_codes:
        locale_path = locales_dir / f"{code}.json"
        assert locale_path.exists(), f"Locale file {locale_path} missing"
        data = json.loads(locale_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"Locale {code} is not a valid dict"
        for k in required_keys:
            assert k in data, f"Required key '{k}' missing from locale {code}"
            assert data[k] != "", f"Key '{k}' in {code} is empty"

    # Verify LanguageContext contains all 7 languages
    lang_ctx_path = WEB_ROOT / "src" / "i18n" / "LanguageContext.tsx"
    lang_ctx = lang_ctx_path.read_text(encoding="utf-8")
    for code in tier1_codes:
        assert f"code: '{code}'" in lang_ctx, f"Code '{code}' not registered in LANGUAGES in LanguageContext"

    # Verify Indic fonts in index.html and index.css
    index_html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
    assert "Noto+Sans+Bengali" in index_html
    assert "Noto+Sans+Devanagari" in index_html
    assert "Noto+Sans+Telugu" in index_html
    assert "Noto+Sans+Tamil" in index_html
    assert "Noto+Sans+Oriya" in index_html

    index_css = (WEB_ROOT / "src" / "index.css").read_text(encoding="utf-8")
    assert "Noto Sans Bengali" in index_css
    assert "Noto Sans Devanagari" in index_css
    assert "Noto Sans Telugu" in index_css
    assert "Noto Sans Tamil" in index_css
    assert "Noto Sans Oriya" in index_css


def test_ml_lab_and_trace_panel_integration():
    """Verify ML Lab feature, TracePanel, and AnswerCard integration in web app (Ticket R17)."""
    # 1. Feature definition
    ml_lab_feature_path = WEB_ROOT / "src" / "features" / "ml-lab" / "feature.ts"
    assert ml_lab_feature_path.exists(), "ml-lab/feature.ts missing"
    feat_text = ml_lab_feature_path.read_text(encoding="utf-8")
    assert "id: 'mllab'" in feat_text or 'id: "mllab"' in feat_text
    assert "/ml-lab" in feat_text

    # 2. MLLabPage component
    ml_lab_page_path = WEB_ROOT / "src" / "features" / "ml-lab" / "MLLabPage.tsx"
    assert ml_lab_page_path.exists(), "ml-lab/MLLabPage.tsx missing"
    page_text = ml_lab_page_path.read_text(encoding="utf-8")
    assert "/v1/ml/models" in page_text
    assert "/v1/ml/eval/summary" in page_text
    assert "/v1/ml/predict/" in page_text
    assert "NOT MEASURED" in page_text

    # 3. TracePanel component
    trace_panel_path = WEB_ROOT / "src" / "features" / "ask" / "TracePanel.tsx"
    assert trace_panel_path.exists(), "ask/TracePanel.tsx missing"
    panel_text = trace_panel_path.read_text(encoding="utf-8")
    assert "TracePanel" in panel_text
    assert "p10" in panel_text and "p90" in panel_text
    assert "SHAP" in panel_text
    assert "Grounding Verifier" in panel_text or "verifier" in panel_text

    # 4. AnswerCard embedding
    answer_card_path = WEB_ROOT / "src" / "features" / "ask" / "AnswerCard.tsx"
    card_text = answer_card_path.read_text(encoding="utf-8")
    assert "TracePanel" in card_text
    assert "traceData" in card_text

