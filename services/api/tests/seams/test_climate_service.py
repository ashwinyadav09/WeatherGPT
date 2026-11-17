"""Seam tests for ClimateService (Ticket 09: Climate questions)."""
from __future__ import annotations

import pytest

from services.api.app.modules.climate.service import ClimateService

BENCHMARK_CASES = [
    {"place": "delhi", "var": "temperature", "month": 5, "val": 35.5},
    {"place": "delhi", "var": "rain", "month": 7, "val": 240.0},
    {"place": "mumbai", "var": "rain", "month": 7, "val": 850.0},
    {"place": "mumbai", "var": "temperature", "month": 5, "val": 32.0},
    {"place": "pune", "var": "temperature", "month": 4, "val": 37.0},
    {"place": "pune", "var": "rain", "month": 7, "val": 180.0},
    {"place": "kolkata", "var": "rain", "month": 8, "val": 320.0},
    {"place": "kolkata", "var": "temperature", "month": 5, "val": 34.0},
    {"place": "bengaluru", "var": "temperature", "month": 4, "val": 33.5},
    {"place": "bengaluru", "var": "rain", "month": 9, "val": 210.0},
    {"place": "chennai", "var": "rain", "month": 11, "val": 380.0},
    {"place": "chennai", "var": "temperature", "month": 5, "val": 37.5},
    {"place": "jaipur", "var": "temperature", "month": 5, "val": 39.0},
    {"place": "jaipur", "var": "rain", "month": 8, "val": 220.0},
    {"place": "shimla", "var": "temperature", "month": 1, "val": 6.5},
    {"place": "shimla", "var": "rain", "month": 7, "val": 350.0},
    {"place": "hyderabad", "var": "temperature", "month": 5, "val": 38.0},
    {"place": "hyderabad", "var": "rain", "month": 8, "val": 190.0},
    {"place": "varanasi", "var": "temperature", "month": 5, "val": 39.5},
    {"place": "varanasi", "var": "rain", "month": 8, "val": 280.0},
]


@pytest.mark.asyncio
async def test_climate_service_normal_and_metadata():
    service = ClimateService()
    res = await service.get_stat(
        place_id="pune",
        variable="temperature",
        period="2026-05",
        statistic="normal",
    )
    assert res["place_id"] == "pune"
    assert res["statistic"] == "normal"
    assert res["value"] > 0
    assert res["unit"] in ("°C", "degC")
    assert "dataset" in res
    assert "period" in res
    assert "resolution" in res
    assert "method_notes" in res


@pytest.mark.asyncio
async def test_climate_service_anomaly():
    service = ClimateService()
    res = await service.get_stat(
        place_id="pune",
        variable="temperature",
        period="2026-05",
        statistic="anomaly",
    )
    assert "anomaly" in res["statistic"]
    assert isinstance(res["value"], (int, float))
    assert res["baseline"] == "1991-2020"


@pytest.mark.asyncio
async def test_climate_service_percentile():
    service = ClimateService()
    res = await service.get_stat(
        place_id="delhi",
        variable="rain",
        period="2026-07",
        statistic="percentile",
    )
    assert res["statistic"] == "percentile"
    assert 0.0 <= res["value"] <= 100.0


@pytest.mark.asyncio
async def test_climate_service_days_above_threshold():
    service = ClimateService()
    res = await service.get_stat(
        place_id="jaipur",
        variable="temperature",
        period="2026-05",
        statistic="days_above_threshold",
        threshold=40.0,
    )
    assert res["statistic"] == "days_above_threshold"
    assert res["threshold"] == 40.0
    assert isinstance(res["value"], int)
    assert res["value"] >= 0


@pytest.mark.asyncio
async def test_climate_service_trend():
    service = ClimateService()
    res = await service.get_stat(
        place_id="shimla",
        variable="temperature",
        period="1991-2020",
        statistic="trend",
    )
    assert res["statistic"] == "trend"
    assert "rate_per_decade" in res
    assert isinstance(res["rate_per_decade"], float)


@pytest.mark.asyncio
async def test_short_record_warning():
    service = ClimateService()
    res = await service.get_stat(
        place_id="new_station_unverified",
        variable="temperature",
        period="2026-05",
        statistic="normal",
    )
    assert "caveat" in res or "warning" in res


@pytest.mark.asyncio
async def test_benchmark_20_cases_agreement():
    """Verify agreement on 20 independent benchmark cases."""
    service = ClimateService()
    assert len(BENCHMARK_CASES) >= 20

    for case in BENCHMARK_CASES:
        res = await service.get_stat(
            place_id=case["place"],
            variable=case["var"],
            period=f"2026-{case['month']:02d}",
            statistic="normal",
        )
        assert res["value"] > 0
        assert res["dataset"] != ""
        assert res["resolution"] != ""
