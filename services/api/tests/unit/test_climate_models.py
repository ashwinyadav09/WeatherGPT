"""Unit tests for Climate Trend, Anomaly, and Extreme Event Models (Ticket R13)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.stats import theilslopes

from ml.climate.models import (
    compute_monthly_normals,
    compute_period_stat,
    compute_trend_mann_kendall,
    evaluate_event_recall,
    fit_isolation_forest_model,
    parse_era5_json_to_df,
)
from services.api.app.agent.tools import get_climate
from services.api.app.modules.climate.service import ClimateService

ROOT = Path(__file__).resolve().parents[4]
CACHE_DIR = ROOT / "ml" / "climate" / "data" / "cache"
EVENTS_FILE = ROOT / "ml" / "climate" / "events.csv"


def test_theil_sen_slope_known_synthetic_series():
    """Unit test with small synthetic series of known slope (allowed in unit tests per spec)."""
    # y = 0.5 * x + 2.0 with slight noise
    x = np.arange(1990, 2020)
    noise = np.array([0.1, -0.1, 0.05, -0.05] * 7 + [0.0, 0.0])
    y = 0.5 * (x - 1990) + 2.0 + noise

    # SciPy direct
    res_scipy = theilslopes(y, x, alpha=0.95)

    # Compute trend via model
    df_syn = pd.DataFrame({
        "year": x,
        "month": 7,
        "day": 15,
        "tmean": y,
        "tmax": y + 5.0,
        "tmin": y - 5.0,
        "precipitation": np.zeros(len(x)),
    })
    trend = compute_trend_mann_kendall(df_syn, variable="temperature", season="annual", start_year=1990, end_year=2019)

    assert abs(res_scipy.slope * 10.0 - trend["slope_per_decade"]) < 1e-4
    assert 4.5 < trend["slope_per_decade"] < 5.5
    assert trend["p_value"] < 0.001
    assert trend["trend"] == "increasing"


def test_leave_one_year_out_stability():
    """Test Leave-One-Year-Out (LOO) slope stability computation."""
    x = np.arange(1990, 2020)
    y = 0.2 * (x - 1990) + 15.0
    df_syn = pd.DataFrame({
        "year": x,
        "month": 5,
        "day": 10,
        "tmean": y,
        "tmax": y + 6.0,
        "tmin": y - 6.0,
        "precipitation": np.ones(len(x)) * 10.0,
    })
    trend = compute_trend_mann_kendall(df_syn, variable="temperature", season="annual", start_year=1990, end_year=2019)
    loo = trend["loo_stability"]

    assert "mean" in loo and "std" in loo
    assert abs(loo["mean"] - 2.0) < 0.01  # 0.2/year = 2.0/decade
    assert loo["std"] < 0.05  # Highly stable for linear series


def test_monthly_normals_computation_real_era5():
    """Compute 1991-2020 normals on real ERA5 data (Delhi 28.50_77.25)."""
    delhi_cache = CACHE_DIR / "28.50_77.25.json"
    if not delhi_cache.exists():
        pytest.skip("Delhi ERA5 cache not downloaded yet")

    raw = json.loads(delhi_cache.read_text(encoding="utf-8"))
    df = parse_era5_json_to_df(raw)
    normals = compute_monthly_normals(df)

    assert normals["baseline_period"] == "1991-2020"
    assert normals["n_years"] == 30
    assert len(normals["temp_c"]) == 12
    assert len(normals["rain_mm"]) == 12

    # Physical checks for Delhi: May/June hottest, Jan coldest, July/August highest rain
    assert normals["temp_c"][4] > normals["temp_c"][0]  # May > Jan
    assert normals["rain_mm"][6] > normals["rain_mm"][3]  # July > April


def test_compute_period_stat_real_data():
    """Test compute_period_stat on real ERA5 records."""
    delhi_cache = CACHE_DIR / "28.50_77.25.json"
    if not delhi_cache.exists():
        pytest.skip("Delhi ERA5 cache not downloaded yet")

    raw = json.loads(delhi_cache.read_text(encoding="utf-8"))
    df = parse_era5_json_to_df(raw)
    normals = compute_monthly_normals(df)

    # Anomaly
    anom = compute_period_stat(df, "temperature", "2024-05", "anomaly", normals)
    assert "value" in anom
    assert "observed" in anom
    assert "normal" in anom
    assert "z_score" in anom

    # Percentile
    pct = compute_period_stat(df, "temperature", "2024-05", "percentile", normals)
    assert 0.0 <= pct["value"] <= 100.0

    # Days above threshold
    days = compute_period_stat(df, "temperature", "2024-05", "days_above_threshold", normals, threshold=40.0)
    assert days["threshold"] == 40.0
    assert isinstance(days["value"], int)


def test_isolation_forest_and_event_recall():
    """Test Isolation Forest fitting and event recall on curated events."""
    if not EVENTS_FILE.exists():
        pytest.skip("events.csv not found")

    delhi_cache = CACHE_DIR / "28.50_77.25.json"
    if not delhi_cache.exists():
        pytest.skip("Delhi ERA5 cache not found")

    raw = json.loads(delhi_cache.read_text(encoding="utf-8"))
    df = parse_era5_json_to_df(raw)

    clf, aux = fit_isolation_forest_model(df)
    assert clf is not None
    assert "iso_pred" in aux["df"].columns
    assert "iso_score" in aux["df"].columns

    # Evaluate event recall
    cell_dfs = {"28.50_77.25": df}
    events_df = pd.read_csv(EVENTS_FILE)
    res = evaluate_event_recall(events_df, cell_dfs)

    assert "isolation_forest_recall" in res
    assert "baseline_recall" in res
    assert "isolation_forest_false_flag_rate" in res
    assert "caveat" in res


@pytest.mark.asyncio
async def test_climate_service_real_evidence_packet():
    """Verify ClimateService integration and evidence packet structure."""
    service = ClimateService()
    res = await service.get_stat(
        place_id="delhi",
        variable="temperature",
        period="2024-05",
        statistic="anomaly",
    )
    assert res["place_id"] == "delhi"
    assert res["variable"] == "temperature"
    assert "z_score" in res
    assert res["is_reanalysis"] is True
    assert "reanalysis values (ERA5)" in res["method_notes"]

    # Trend stat
    trend_res = await service.get_stat(
        place_id="delhi",
        variable="temperature",
        statistic="trend",
    )
    assert trend_res["statistic"] == "trend"
    assert "p_value" in trend_res
    assert "rate_per_decade" in trend_res
    assert "ci_95" in trend_res
    assert "n_years" in trend_res


@pytest.mark.asyncio
async def test_get_climate_tool_evidence_packet():
    """Verify get_climate tool returns evidence packets with p_value, n_years, and source."""
    packets = await get_climate(place="delhi", metric="temperature", statistic="trend")
    assert len(packets) >= 1
    pkt = packets[0]
    assert pkt.source == "ERA5 via Open-Meteo"
    assert pkt.authority_tier == 3
    assert any(v.variable == "rate_per_decade" for v in pkt.values)
    assert any(v.variable == "p_value" for v in pkt.values)
