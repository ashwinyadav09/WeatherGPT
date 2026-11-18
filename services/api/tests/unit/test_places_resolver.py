from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from services.api.app.modules.location.resolver import LocationResolver

ROOT = Path(__file__).resolve().parents[4]
GOLDEN_PATH = ROOT / "eval" / "golden" / "places_golden.yaml"


@pytest.fixture
def resolver() -> LocationResolver:
    return LocationResolver()


@pytest.mark.asyncio
async def test_places_golden_set_accuracy(resolver: LocationResolver):
    assert GOLDEN_PATH.exists(), f"Golden cases file missing at {GOLDEN_PATH}"
    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cases = data.get("cases", [])
    assert len(cases) >= 200, f"Expected at least 200 cases, found {len(cases)}"

    district_total = 0
    district_correct = 0

    panchayat_total = 0
    panchayat_correct = 0

    for case in cases:
        query = case["query"]
        expected_level = case.get("expected_level", "district")

        res = await resolver.resolve(query)
        resolved_place = res.get("resolved_place")
        assert resolved_place is not None, f"No place returned for query: {query}"
        assert isinstance(resolved_place.lat, float)
        assert isinstance(resolved_place.lon, float)

        # Check GPS
        if case.get("is_gps"):
            panchayat_total += 1
            if (
                abs(resolved_place.lat - case["expected_lat"]) < 0.001
                and abs(resolved_place.lon - case["expected_lon"]) < 0.001
            ):
                panchayat_correct += 1
            continue

        # Check Ambiguity
        if case.get("is_ambiguous"):
            district_total += 1
            if res.get("ambiguous") is True and res.get("clarification_question"):
                district_correct += 1
            continue

        # Check Expected ID match
        expected_id = case.get("expected_id")
        matched = resolved_place.id == expected_id

        if expected_level == "district":
            district_total += 1
            if matched:
                district_correct += 1
        else:
            panchayat_total += 1
            if matched:
                panchayat_correct += 1

    district_acc = (district_correct / district_total) * 100 if district_total else 0.0
    panchayat_acc = (panchayat_correct / panchayat_total) * 100 if panchayat_total else 0.0

    print("\n--- Place Golden Set Results ---")
    print(f"Total Cases: {len(cases)}")
    print(f"District Level: {district_correct}/{district_total} ({district_acc:.1f}%) [Threshold: >= 95%]")
    print(f"Panchayat/Block/Village Level: {panchayat_correct}/{panchayat_total} ({panchayat_acc:.1f}%) [Threshold: >= 85%]")

    assert district_acc >= 95.0, f"District accuracy {district_acc:.1f}% below 95% threshold"
    assert panchayat_acc >= 85.0, f"Panchayat accuracy {panchayat_acc:.1f}% below 85% threshold"


@pytest.mark.asyncio
async def test_ambiguity_clarification_question(resolver: LocationResolver):
    res_en = await resolver.resolve("Bilaspur", language="en")
    assert res_en["ambiguous"] is True
    assert "Did you mean" in res_en["clarification_question"]
    assert "Chhattisgarh" in res_en["clarification_question"]
    assert "Himachal Pradesh" in res_en["clarification_question"]

    res_hi = await resolver.resolve("बिलासपुर", language="hi")
    assert res_hi["ambiguous"] is True
    assert "क्या आपका मतलब" in res_hi["clarification_question"]


@pytest.mark.asyncio
async def test_transliteration_and_indic_equivalence(resolver: LocationResolver):
    pune_en = await resolver.resolve("Pune")
    pune_alias = await resolver.resolve("Poona")
    pune_hi = await resolver.resolve("पुणे")
    pune_hi_alias = await resolver.resolve("पुना")

    assert pune_en["resolved_place"].id == "pune"
    assert pune_alias["resolved_place"].id == "pune"
    assert pune_hi["resolved_place"].id == "pune"
    assert pune_hi_alias["resolved_place"].id == "pune"
    assert pune_en["resolved_place"].lat == pune_hi["resolved_place"].lat


@pytest.mark.asyncio
async def test_saved_places_resolution(resolver: LocationResolver):
    res_home = await resolver.resolve("home")
    assert res_home["resolved_place"].id == "saved_home"
    assert res_home["resolved_place"].district == "Pune"

    res_farm = await resolver.resolve("खेत")
    assert res_farm["resolved_place"].id == "saved_farm"
    assert res_farm["resolved_place"].district == "Pune"
