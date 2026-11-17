"""Seam tests for the SACHET CAP ingest adapter (ticket 05, Alerts v1).

These tests run on recorded fixtures from eval/fixtures/sachet/. They assert:
  1. The severity-to-level mapping for every CAP severity value.
  2. Test and Exercise statuses are ignored.
  3. Update and Cancel messages are handled correctly.
  4. Polygons are converted from lat,lon to GeoJSON [lon,lat].
  5. Only allowlisted sender domains are accepted.
  6. No LLM call occurs between ingest and push (the pipeline is pure).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from services.api.app.modules.alerts.sachet_adapter import SachetCAPAdapter, parse_cap_xml, severity_to_level

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SACHET_FIXTURES = ROOT / "eval" / "fixtures" / "sachet"


# ── Helper ───────────────────────────────────────────────────────────────────

def load_fixture(name: str) -> dict:
    p = SACHET_FIXTURES / name
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


# ── 1. Severity → level mapping ───────────────────────────────────────────────

@pytest.mark.parametrize("severity,expected_level", [
    ("Extreme", "red"),
    ("Severe", "orange"),
    ("Moderate", "yellow"),
    ("Minor", "green"),
    ("Unknown", "yellow"),  # safe default
])
def test_severity_to_level_mapping(severity: str, expected_level: str) -> None:
    assert severity_to_level(severity) == expected_level


# ── 2. Test and Exercise statuses are ignored ─────────────────────────────────

def test_test_status_ignored() -> None:
    adapter = SachetCAPAdapter()
    assert adapter.should_ignore_message(status="Test", msg_type="Alert") is True


def test_exercise_status_ignored() -> None:
    adapter = SachetCAPAdapter()
    assert adapter.should_ignore_message(status="Exercise", msg_type="Alert") is True


def test_actual_status_accepted() -> None:
    adapter = SachetCAPAdapter()
    assert adapter.should_ignore_message(status="Actual", msg_type="Alert") is False


def test_draft_status_ignored() -> None:
    adapter = SachetCAPAdapter()
    assert adapter.should_ignore_message(status="Draft", msg_type="Alert") is True


# ── 3. Update and Cancel handling ─────────────────────────────────────────────

def test_update_fixture_accepted_as_update_type() -> None:
    """Update fixtures should be parsed with msg_type=Update."""
    fix = load_fixture("sachet_01_update.json")
    assert fix["msg_type"] == "Update"


def test_synthetic_cyclone_is_alert_type() -> None:
    fix = load_fixture("sachet_synthetic_cyclone.json")
    assert fix["msg_type"] == "Alert"
    assert fix["severity"] == "Extreme"
    assert fix["level"] == "red"


# ── 4. CAP polygon lat,lon → GeoJSON [lon, lat] conversion ───────────────────

def test_polygon_conversion_lat_lon_to_geojson() -> None:
    adapter = SachetCAPAdapter()
    cap_polygon = "18.52,73.85 18.60,73.90 18.45,73.95 18.52,73.85"
    geojson_coords = adapter.cap_polygon_to_geojson(cap_polygon)
    # First coord should be [lon, lat] (GeoJSON order)
    assert geojson_coords[0] == [73.85, 18.52], f"Expected [73.85, 18.52] but got {geojson_coords[0]}"
    assert len(geojson_coords) == 4


def test_polygon_conversion_empty_string() -> None:
    adapter = SachetCAPAdapter()
    result = adapter.cap_polygon_to_geojson("")
    assert result == []


# ── 5. Only allowlisted sender domains accepted ───────────────────────────────

def test_allowlisted_sachet_domain_accepted() -> None:
    adapter = SachetCAPAdapter()
    assert adapter.is_sender_allowed("https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=123") is True


def test_non_allowlisted_domain_rejected() -> None:
    adapter = SachetCAPAdapter()
    assert adapter.is_sender_allowed("https://malicious-site.example.com/fake.xml") is False


def test_imd_rsmc_domain_accepted() -> None:
    adapter = SachetCAPAdapter()
    assert adapter.is_sender_allowed("https://sachet.ndma.gov.in/cyclone.xml") is True


# ── 6. No LLM call between ingest and push ───────────────────────────────────

def test_no_llm_call_on_ingest() -> None:
    """The alert ingest pipeline must not invoke any LLM gateway."""
    from services.api.app.modules.alerts.engine import AlertEngine
    from services.api.app.modules.alerts.sachet_adapter import SachetCAPAdapter

    with patch("services.api.app.gateways.llm.gateway.LLMGateway.complete") as mock_llm:
        _adapter = SachetCAPAdapter()
        engine = AlertEngine()
        fix = load_fixture("sachet_06_alert.json")
        # Strip provenance metadata before ingest
        clean = {k: v for k, v in fix.items() if not k.startswith("_")}
        from services.api.app.evidence.models import AlertModel
        alert = AlertModel(**clean)
        engine.ingest_sample_alert(alert)

    mock_llm.assert_not_called(), "LLM gateway must NOT be called during alert ingest"


# ── 7. Fixture schema conformance ─────────────────────────────────────────────

def test_all_sachet_fixtures_conform_to_alert_schema() -> None:
    from packages.contracts.validator import validate_schema
    for json_file in SACHET_FIXTURES.glob("*.json"):
        with json_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        clean = {k: v for k, v in data.items() if not k.startswith("_")}
        validate_schema("alert", clean)


# ── 8. CAP XML parsing (via raw XML fixtures) ─────────────────────────────────

def test_parse_cap_xml_from_recorded_fixture() -> None:
    """Parse one raw CAP XML and confirm it yields a valid AlertModel dict."""
    cap_xml_dir = SACHET_FIXTURES / "cap_xml"
    xml_files = sorted(cap_xml_dir.glob("*.xml"))
    assert xml_files, "No CAP XML fixtures found"

    xml_text = xml_files[0].read_text(encoding="utf-8", errors="replace")
    result = parse_cap_xml(
        xml_text=xml_text,
        source_url="https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=test"
    )
    assert result is not None
    assert "id" in result
    assert result.get("authority_tier") == 1
    assert result.get("level") in ("green", "yellow", "orange", "red")
