"""Unit tests for Provider Registry (Ticket R1.1).

Requirements:
- Configuration: FORECAST_PROVIDERS=open_meteo, ALERT_PROVIDERS=sachet, TRANSLATION_PROVIDERS=sarvam,llm, SPEECH_PROVIDERS=sarvam.
- Order = priority; the first healthy provider answers; failures fall through and are logged.
- Keep imd_city registered but excluded unless IMD_ENABLED=true and a key exists.
- Switching FORECAST_PROVIDERS changes the active provider without code changes.
"""
from __future__ import annotations

import datetime as dt
import logging
from unittest.mock import AsyncMock

import pytest

from services.api.app.config import Settings
from services.api.app.evidence.models import EvidencePacket, PlaceReference
from services.api.app.modules.forecast.adapters.ecmwf import ECMWFAdapter
from services.api.app.modules.forecast.adapters.gfs import GFSPointAdapter
from services.api.app.modules.forecast.adapters.imd_city import IMDCityForecastAdapter
from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
from services.api.app.modules.forecast.adapters.stub import StubForecastAdapter
from services.api.app.registry import (
    FailoverForecastProvider,
    ProviderRegistry,
)


def test_default_providers_registered_and_resolved():
    """Default configuration should resolve open_meteo, sachet, and sarvam."""
    reg = ProviderRegistry()
    active_forecast = reg.get_active_forecast_provider()
    assert isinstance(active_forecast, OpenMeteoForecastAdapter)

    alert_adapter = reg.get_alert_adapter()
    assert alert_adapter is not None
    assert type(alert_adapter).__name__ == "SachetCAPAdapter"

    speech_adapter = reg.get_speech_adapter()
    assert speech_adapter is not None
    assert type(speech_adapter).__name__ == "SarvamSpeechAdapter"


def test_switching_forecast_providers_changes_active_provider():
    """Switching FORECAST_PROVIDERS environment variable changes the active provider."""
    # 1. Switch to GFS
    settings_gfs = Settings(forecast_providers=["gfs"])
    reg_gfs = ProviderRegistry(settings=settings_gfs)
    assert isinstance(reg_gfs.get_active_forecast_provider(), GFSPointAdapter)

    # 2. Switch to ECMWF
    settings_ecmwf = Settings(forecast_providers=["ecmwf"])
    reg_ecmwf = ProviderRegistry(settings=settings_ecmwf)
    assert isinstance(reg_ecmwf.get_active_forecast_provider(), ECMWFAdapter)

    # 3. Switch to stub
    settings_stub = Settings(forecast_providers=["stub"])
    reg_stub = ProviderRegistry(settings=settings_stub)
    assert isinstance(reg_stub.get_active_forecast_provider(), StubForecastAdapter)


def test_imd_city_registered_but_excluded_unless_flag_and_key():
    """imd_city must be excluded unless IMD_ENABLED is true and IMD_API_KEY is non-empty."""
    # Case 1: IMD in providers, but IMD_ENABLED is false -> excluded, falls through to open_meteo
    settings_no_flag = Settings(
        forecast_providers=["imd_city", "open_meteo"],
        imd_enabled=False,
        imd_api_key="secret-key",
    )
    reg1 = ProviderRegistry(settings=settings_no_flag)
    active1 = reg1.get_active_forecast_provider()
    assert isinstance(active1, OpenMeteoForecastAdapter)
    available_names = [p.source_id for p in reg1.get_available_forecast_providers()]
    assert "imd.city_forecast" not in available_names

    # Case 2: IMD_ENABLED is true, but IMD_API_KEY is empty -> excluded
    settings_no_key = Settings(
        forecast_providers=["imd_city", "open_meteo"],
        imd_enabled=True,
        imd_api_key="",
    )
    reg2 = ProviderRegistry(settings=settings_no_key)
    active2 = reg2.get_active_forecast_provider()
    assert isinstance(active2, OpenMeteoForecastAdapter)
    available_names2 = [p.source_id for p in reg2.get_available_forecast_providers()]
    assert "imd.city_forecast" not in available_names2

    # Case 3: IMD_ENABLED is true AND IMD_API_KEY is present -> included and active
    settings_live_imd = Settings(
        forecast_providers=["imd_city", "open_meteo"],
        imd_enabled=True,
        imd_api_key="valid-key",
    )
    reg3 = ProviderRegistry(settings=settings_live_imd)
    active3 = reg3.get_active_forecast_provider()
    assert isinstance(active3, IMDCityForecastAdapter)


@pytest.mark.asyncio
async def test_failover_provider_priority_and_logging(caplog):
    """FailoverForecastProvider tries providers in priority order; failures fall through and are logged."""
    mock_failing_p1 = AsyncMock()
    mock_failing_p1.source_id = "mock.failing"
    mock_failing_p1.get_forecast.side_effect = RuntimeError("Service network timeout")

    sample_packet = EvidencePacket(
        id="pkt_mock_1",
        source="mock.fallback",
        authority_tier=5,
        provenance="live",
        issued_at=dt.datetime(2026, 11, 22, 12, 0, tzinfo=dt.timezone.utc),
        valid_from=dt.datetime(2026, 11, 23, 0, 0, tzinfo=dt.timezone.utc),
        valid_to=dt.datetime(2026, 11, 23, 23, 59, 59, tzinfo=dt.timezone.utc),
        place=PlaceReference(id="pune", name="Pune", lat=18.5204, lon=73.8567),
        values=[],
        attribution="Fallback data",
    )
    mock_healthy_p2 = AsyncMock()
    mock_healthy_p2.source_id = "mock.healthy"
    mock_healthy_p2.get_forecast.return_value = [sample_packet]

    failover = FailoverForecastProvider(providers=[mock_failing_p1, mock_healthy_p2])

    with caplog.at_level(logging.WARNING):
        result = await failover.get_forecast(lat=18.52, lon=73.85, place_name="Pune")

    # Result came from mock_healthy_p2
    assert result == [sample_packet]
    mock_failing_p1.get_forecast.assert_awaited_once()
    mock_healthy_p2.get_forecast.assert_awaited_once()

    # The failure of p1 was logged with provider and error info
    assert any(
        "forecast_provider_failed" in rec.message or "Service network timeout" in rec.message
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_all_providers_failing_raises():
    """If all providers fail, FailoverForecastProvider raises RuntimeError."""
    mock_failing = AsyncMock()
    mock_failing.source_id = "mock.failing"
    mock_failing.get_forecast.side_effect = RuntimeError("Crash")

    failover = FailoverForecastProvider(providers=[mock_failing])
    with pytest.raises(RuntimeError, match="All forecast providers failed"):
        await failover.get_forecast(lat=18.52, lon=73.85, place_name="Pune")
