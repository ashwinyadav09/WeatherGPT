from __future__ import annotations

import json
from pathlib import Path

from eval.fixtures.loader import get_fixture, list_fixtures, load_fixture_index, validate_fixture_provenance

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


def test_fixture_loader_and_index():
    index = load_fixture_index()
    assert isinstance(index, list)
    assert len(index) >= 50

    # Every item has source, file, provenance, date, url
    for item in index:
        assert "source" in item
        assert "file" in item
        assert "provenance" in item
        assert item["provenance"] in ("live-recorded", "documented-sample", "spec-only", "synthetic")
        assert "date" in item
        assert "url" in item
        file_path = ROOT / item["file"]
        assert file_path.exists(), f"Indexed fixture file missing: {file_path}"


def test_sachet_fixtures():
    fixtures = list_fixtures(source="sachet")
    # At least 20 real CAP samples plus 1 synthetic cyclone sample
    assert len(fixtures) >= 21
    synthetic = [f for f in fixtures if f.get("provenance") == "synthetic"]
    assert len(synthetic) >= 1
    assert any("cyclone" in f.get("file", "").lower() or "cyclone" in f.get("hazard", "").lower() for f in synthetic)


def test_open_meteo_fixtures():
    fixtures = list_fixtures(source="open_meteo")
    # At least 10 places with forecast, archive and geocoding
    forecasts = [f for f in fixtures if "forecast" in f.get("file", "")]
    archives = [f for f in fixtures if "archive" in f.get("file", "")]
    geocodings = [f for f in fixtures if "geocoding" in f.get("file", "")]

    assert len(forecasts) >= 10
    assert len(archives) >= 10
    assert len(geocodings) >= 10


def test_aviation_and_iem_fixtures():
    awc = list_fixtures(source="aviationweather")
    iem = list_fixtures(source="iem")

    metar = [f for f in awc if "metar" in f.get("file", "")]
    taf = [f for f in awc if "taf" in f.get("file", "")]

    assert len(metar) >= 5
    assert len(taf) >= 5
    assert len(iem) >= 5


def test_geonames_seed():
    seed_file = ROOT / "seeds" / "places" / "geonames_india_seed.json"
    rebuild_script = ROOT / "scripts" / "build_geonames_seed.py"

    assert seed_file.exists(), f"GeoNames seed file missing: {seed_file}"
    assert rebuild_script.exists(), f"GeoNames rebuild script missing: {rebuild_script}"

    with seed_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) >= 10
    # Check for Indic / Hindi names
    has_indic = any(
        any(ord(c) >= 0x0900 and ord(c) <= 0x0D7F for c in str(p.get("names", {}).values()))
        for p in data
    )
    assert has_indic, "GeoNames seed must include Indic/Hindi names"


def test_imd_fixtures():
    fixtures = list_fixtures(source="imd")
    assert len(fixtures) >= 10
    for f in fixtures:
        assert f.get("provenance") in ("documented-sample", "spec-only")


def test_no_fixture_contains_keys():
    for f in list_fixtures():
        data = get_fixture(f["file"])
        if isinstance(data, dict) and "_provenance" in data:
            assert validate_fixture_provenance(data) in ("live-recorded", "documented-sample", "spec-only", "synthetic")
        text = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
        assert "sk-" not in text
        assert "gsk_" not in text
        assert "AIza" not in text
