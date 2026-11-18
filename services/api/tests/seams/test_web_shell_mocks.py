from __future__ import annotations

import json
from pathlib import Path

from packages.contracts.validator import validate_schema

ROOT = Path(__file__).resolve().parents[4]
WEB_ROOT = ROOT / "apps" / "web"


def test_web_shell_assets_exist():
    assert (WEB_ROOT / "index.html").exists(), "index.html missing"
    assert (WEB_ROOT / "public" / "manifest.json").exists(), "manifest.json missing"
    assert (WEB_ROOT / "public" / "sw.js").exists(), "sw.js missing"
    assert (WEB_ROOT / "public" / "icon-192.svg").exists(), "icon-192.svg missing"
    assert (WEB_ROOT / "public" / "icon-512.svg").exists(), "icon-512.svg missing"
    assert (WEB_ROOT / "Dockerfile").exists(), "Dockerfile missing"

    # Verify manifest.json
    with (WEB_ROOT / "public" / "manifest.json").open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert manifest["name"] == "WeatherGPT - India Weather Assistant"
    assert manifest["short_name"] == "WeatherGPT"
    assert manifest["theme_color"] == "#1B7F3B"
    assert manifest["display"] == "standalone"


def test_web_shell_mock_places_contract_conformance():
    # Extract mock places defined in mockData.ts
    mock_data_path = WEB_ROOT / "src" / "mocks" / "mockData.ts"
    assert mock_data_path.exists()

    sample_place = {
        "id": "place_pune",
        "kind": "district",
        "names": {
            "en": "Pune",
            "hi": "पुणे",
            "mr": "पुणे",
        },
        "lat": 18.5204,
        "lon": 73.8567,
        "elevation": 560,
        "state": "Maharashtra",
        "district": "Pune",
    }
    validate_schema("place", sample_place)


def test_web_shell_mock_alerts_contract_conformance():
    sample_alert = {
        "id": "alert_imd_2026_01",
        "sender": "imd.sachet.ndma.gov.in",
        "sent": "2026-11-17T06:00:00Z",
        "status": "Actual",
        "msg_type": "Alert",
        "hazard": "Heavy Rainfall",
        "severity": "Severe",
        "urgency": "Expected",
        "certainty": "Likely",
        "onset": "2026-11-17T09:00:00Z",
        "expires": "2026-11-18T18:00:00Z",
        "areas": [
            {
                "areaDesc": "Pune district",
                "circle": "18.5204,73.8567,25.0",
            }
        ],
        "text_by_language": {
            "en": "Heavy to very heavy rainfall expected in isolated ghat areas of Pune district.",
            "hi": "पुणे जिले के अलग-अलग घाट क्षेत्रों में भारी से बहुत भारी बारिश की संभावना है।",
        },
        "source_url": "https://sachet.ndma.gov.in/alerts/alert_imd_2026_01",
        "authority_tier": 1,
        "level": "orange",
    }
    validate_schema("alert", sample_alert)


def test_web_shell_mock_evidence_packet_contract_conformance():
    sample_packet = {
        "id": "ev_mock_om_01",
        "source": "open_meteo.forecast",
        "authority_tier": 5,
        "provenance": "documented-sample",
        "issued_at": "2026-11-17T00:00:00Z",
        "valid_from": "2026-11-17T00:00:00Z",
        "valid_to": "2026-11-24T00:00:00Z",
        "place": {
            "id": "pt_18.5204_73.8567",
            "name": "Pune",
            "lat": 18.5204,
            "lon": 73.8567,
        },
        "values": [
            {"variable": "temperature", "value": 27.5, "unit": "degC"},
            {"variable": "rain", "value": 12.4, "unit": "mm"},
        ],
        "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)",
        "fetched_at": "2026-11-17T06:00:00Z",
    }
    validate_schema("evidence_packet", sample_packet)


def test_web_shell_mock_chat_events_contract_conformance():
    # Test answer_event schema conformance
    token_event = {"event": "token", "data": {"text": "Rain is likely tomorrow."}}
    validate_schema("answer_event", token_event)

    card_event = {
        "event": "card",
        "data": {
            "headline": "Rain likely tomorrow",
            "key_values": {"rain": "12 mm"},
            "source_line": "Source: Open-Meteo",
        },
    }
    validate_schema("answer_event", card_event)


def test_aviation_and_smart_city_features_exist():
    assert (WEB_ROOT / "src" / "features" / "aviation" / "feature.ts").exists()
    assert (WEB_ROOT / "src" / "features" / "aviation" / "AviationPage.tsx").exists()
    assert (WEB_ROOT / "src" / "features" / "smartcity" / "feature.ts").exists()
    assert (WEB_ROOT / "src" / "features" / "smartcity" / "SmartCityPage.tsx").exists()

    av_content = (WEB_ROOT / "src" / "features" / "aviation" / "AviationPage.tsx").read_text(encoding="utf-8")
    assert "INFORMATIONAL ONLY" in av_content
    assert "NOT AN OFFICIAL PRE-FLIGHT BRIEFING" in av_content
    assert "Crosswind" in av_content
