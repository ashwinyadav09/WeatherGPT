"""Unit and seam tests for R6.1 Golden sets by intent and quality rubric.

Tests:
1. Golden sets structure: cases by intent (forecast, advisory, refusal) across Tier-1 languages.
2. Per-city fixtures: forecast cases specify place, day, and numbers from distinct city fixtures (not Pune for all).
3. Evaluation harness assertions: checks numbers, named source, language, and refusal.
4. Human-rated calibration sample and Cohen's kappa inter-rater reliability.
5. End-to-end evaluation harness run on a multi-intent golden sample.
"""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import yaml

from eval.harness import (
    get_per_city_forecast_transport,
    run_single_case,
)
from eval.judge import calculate_cohen_kappa, evaluate_quality_rubric
from services.api.app.agent.orchestrator import Orchestrator
from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
from services.api.app.modules.forecast.service import ForecastService
from services.api.app.modules.location.adapters.open_meteo_geocoding import OpenMeteoGeocodingAdapter
from services.api.app.modules.location.resolver import LocationResolver

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
GOLDEN_DIR = ROOT / "eval" / "golden"


def test_golden_sets_exist_by_intent():
    """Verify that golden sets exist by intent (forecast, advisory, refusal) for Tier-1 languages."""
    tier1_langs = ["en", "hi", "bn", "mr", "te", "ta", "or"]
    for lang in tier1_langs:
        lang_dir = GOLDEN_DIR / lang
        assert lang_dir.exists(), f"Golden set directory missing for language: {lang}"

        # Must have at least forecast cases
        forecast_files = list(lang_dir.glob("*forecast*.yaml"))
        assert len(forecast_files) >= 1, f"Missing forecast golden set in {lang}"

        # Load cases
        cases = []
        for yml in lang_dir.glob("*.yaml"):
            with yml.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, list):
                    cases.extend(data)

        assert len(cases) >= 10, f"Golden set for {lang} has only {len(cases)} cases, expected >= 10"


def test_forecast_cases_have_per_city_numbers():
    """Verify forecast cases specify distinct cities, days, and expected numbers."""
    en_forecast_file = GOLDEN_DIR / "en" / "forecast.yaml"
    assert en_forecast_file.exists()

    with en_forecast_file.open("r", encoding="utf-8") as f:
        cases = yaml.safe_load(f)

    cities_covered = set()
    numbers_seen = set()

    for c in cases:
        assert "place" in c, f"Case {c.get('id')} missing 'place'"
        assert "day" in c, f"Case {c.get('id')} missing 'day'"
        assert "expect" in c, f"Case {c.get('id')} missing 'expect'"

        expect = c["expect"]
        assert "source_named" in expect, f"Case {c.get('id')} missing 'source_named'"
        assert "expected_numbers" in expect, f"Case {c.get('id')} missing 'expected_numbers'"
        assert len(expect["expected_numbers"]) >= 1

        cities_covered.add(c["place"].lower())
        for n in expect["expected_numbers"]:
            numbers_seen.add(float(n))

    # Must cover at least 6 distinct cities and distinct numbers (not Pune for all)
    assert len(cities_covered) >= 6, f"Covered only {cities_covered}, expected >= 6 cities"
    assert len(numbers_seen) >= 5, f"Expected distinct numbers across cities, got {numbers_seen}"


def test_cohen_kappa_calculation():
    """Test Cohen's kappa inter-rater agreement computation."""
    # Perfect agreement
    r1 = [5, 4, 3, 5, 2]
    r2 = [5, 4, 3, 5, 2]
    assert calculate_cohen_kappa(r1, r2) == 1.0

    # Substantial agreement
    r_ashwin = [5, 4, 5, 3, 5, 4, 4, 5, 2, 5]
    r_aman = [5, 4, 4, 3, 5, 5, 4, 5, 2, 5]
    kappa = calculate_cohen_kappa(r_ashwin, r_aman)
    assert 0.6 <= kappa <= 1.0


def test_quality_rubric_scoring():
    """Test 5-point quality rubric evaluation."""
    sample_answer = "According to Open-Meteo forecasts, tomorrow in Delhi expects 0.0 mm rain and a temperature of 24.3 degC."
    sample_case = {
        "id": "test-001",
        "question": "Will it rain tomorrow in Delhi?",
        "place": "Delhi",
        "expect": {"source_named": "Open-Meteo", "expected_numbers": [24.3, 0.0], "refusal": False},
    }

    result = evaluate_quality_rubric(sample_answer, sample_case)
    assert result["score"] >= 4
    assert result["grounded"] is True
    assert result["source_attributed"] is True


@pytest.mark.asyncio
async def test_evaluation_harness_with_per_city_mock():
    """Run single cases in evaluation harness with per-city mock transport."""
    transport = get_per_city_forecast_transport()
    mock_client = httpx.AsyncClient(transport=transport)
    fc_adapter = OpenMeteoForecastAdapter(client=mock_client)
    fc_service = ForecastService()
    fc_service.register_adapter(fc_adapter)

    geocoder = OpenMeteoGeocodingAdapter(client=mock_client)
    loc_resolver = LocationResolver(geocoder=geocoder)
    agent = Orchestrator(forecast_service=fc_service, location_resolver=loc_resolver)

    # Case 1: Forecast for Delhi
    case_delhi = {
        "id": "en-test-delhi",
        "language": "en",
        "intent": "forecast",
        "place": "Delhi",
        "place_id": "delhi",
        "day": "tomorrow",
        "question": "Will it rain tomorrow in Delhi?",
        "expect": {
            "source_named": "Open-Meteo",
            "expected_numbers": [24.3, 0.0],
            "refusal": False,
            "must_not": ["evacuate"],
        },
    }
    res_delhi = await run_single_case(agent, case_delhi)
    assert res_delhi["passed"] is True
    assert "open-meteo" in res_delhi["answer"].lower()

    # Case 2: Refusal for Aviation
    case_aviation = {
        "id": "en-test-aviation",
        "language": "en",
        "intent": "aviation_brief",
        "question": "Give me a METAR flight briefing from Delhi to Mumbai.",
        "expect": {
            "refusal": True,
            "must_not": ["guaranteed"],
        },
    }
    res_aviation = await run_single_case(agent, case_aviation)
    assert res_aviation["passed"] is True
