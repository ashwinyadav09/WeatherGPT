"""Seam tests for Point-Forecast Bias Correction (Ticket 16 / R8.2).

Per Rule T3: Synthetic fixtures are allowed only inside unit/seam tests to verify
algorithms and mathematical routines, and never in production code or reported benchmarks.
"""

from __future__ import annotations

import datetime as dt
import math

import pytest

from ml.bias_correction.dataset import get_dataset_manifest
from ml.bias_correction.mos_model import PointForecastMOSModel
from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem
from services.api.app.modules.forecast.bias_corrector import apply_bias_correction_to_forecast


def _make_unit_test_records(n: int = 50) -> list[dict]:
    """Generates synthetic records strictly for seam testing mathematical methods (Rule T3)."""
    records = []
    base_date = dt.date(2023, 1, 1)
    for i in range(n):
        d = base_date + dt.timedelta(days=i * 5)
        doy = d.timetuple().tm_yday
        seasonal = 25.0 + 5.0 * math.sin(doy * 2 * math.pi / 365.0)
        true_t = seasonal + (i % 3 - 1) * 0.5
        # Raw model has positive systematic bias (+2.0 C)
        raw_t = true_t + 2.0
        # Rain simulation
        is_rain = (i % 4 == 0)
        obs_rain = 8.0 if is_rain else 0.0
        raw_rain = 6.0 if is_rain else (2.0 if i % 3 == 0 else 0.0)

        records.append({
            "date": d.isoformat(),
            "year": d.year,
            "month": d.month,
            "day_of_year": doy,
            "station_id": "TEST",
            "station_name": "TestStation",
            "lat": 20.0,
            "lon": 73.0,
            "elevation": 200.0,
            "lead_time_hours": 24,
            "raw_temp_forecast": raw_t,
            "raw_rain_forecast": raw_rain,
            "observed_temp": true_t,
            "observed_rain": obs_rain,
            "observed_rain_event": 1 if is_rain else 0,
            "persistence_temp": true_t + 1.5,
            "persistence_rain": obs_rain,
            "climatology_temp": seasonal,
            "climatology_rain": 4.0,
        })
    return records


@pytest.fixture
def mos_model() -> PointForecastMOSModel:
    model = PointForecastMOSModel()
    train_records = _make_unit_test_records(60)
    model.train(train_data=train_records)
    # Enable test skill gates for 24h lead time
    model.val_skill = {
        "temperature_2m": {24: True, 48: True, 240: False},
        "precipitation": {24: True, 48: True, 240: False},
    }
    model.rain_weights = [-1.5, 0.45, 0.85, 1.1, -0.05]
    return model


def test_dataset_manifest_licences():
    manifest = get_dataset_manifest()
    assert "open_meteo" in manifest
    assert "iem_metar" in manifest
    assert "gfs_archive" in manifest
    assert manifest["open_meteo"]["licence"] == "CC BY 4.0"
    assert "open" in manifest["iem_metar"]["licence"].lower()


def test_temperature_mos_evaluation_vs_baselines(mos_model: PointForecastMOSModel):
    test_records = _make_unit_test_records(40)
    report = mos_model.evaluate_temperature(test_data=test_records)

    # Must report MAE and RMSE for MOS, Raw Model, Persistence, and Climatology
    assert "mos" in report
    assert "raw_model" in report
    assert "persistence" in report
    assert "climatology" in report

    mos_mae = report["mos"]["mae"]
    raw_mae = report["raw_model"]["mae"]
    persist_mae = report["persistence"]["mae"]
    clim_mae = report["climatology"]["mae"]

    print(
        f"\nTemperature MAE: MOS={mos_mae:.2f}°C, Raw={raw_mae:.2f}°C, Persist={persist_mae:.2f}°C, Clim={clim_mae:.2f}°C"
    )

    # MOS must reduce MAE over raw model, persistence and climatology on biased test records
    assert mos_mae < raw_mae, f"MOS MAE ({mos_mae}) must beat raw model ({raw_mae})"
    assert mos_mae < persist_mae, f"MOS MAE ({mos_mae}) must beat persistence ({persist_mae})"
    assert mos_mae < clim_mae, f"MOS MAE ({mos_mae}) must beat climatology ({clim_mae})"
    assert report["mos"]["rmse"] < report["raw_model"]["rmse"]


def test_rain_event_metrics_and_reliability_diagram(mos_model: PointForecastMOSModel):
    test_records = _make_unit_test_records(40)
    rain_report = mos_model.evaluate_precipitation(test_data=test_records)

    assert "pod" in rain_report["mos"]
    assert "far" in rain_report["mos"]
    assert "csi" in rain_report["mos"]

    # Reliability diagram calibration bins
    diagram = mos_model.generate_reliability_diagram(test_data=test_records)
    assert len(diagram["bins"]) >= 4, "Reliability diagram must have at least 4 probability bins"
    for b in diagram["bins"]:
        assert "prob_range" in b
        assert "forecast_prob" in b
        assert "observed_freq" in b
        assert "count" in b


def test_gated_correction_lead_time_policy(mos_model: PointForecastMOSModel):
    # For lead times where MOS beats raw model, correction is approved
    assert mos_model.should_use_correction(variable="temperature_2m", lead_time_hours=24) is True
    assert mos_model.should_use_correction(variable="precipitation", lead_time_hours=24) is True

    # At distant lead times (e.g. 240h), gate policy must reject correction
    assert mos_model.should_use_correction(variable="temperature_2m", lead_time_hours=240) is False


def test_evidence_packet_model_guidance_and_never_overrides_official(mos_model: PointForecastMOSModel):
    now = dt.datetime.now(dt.timezone.utc)
    place = PlaceReference(id="delhi", name="Delhi", lat=28.6139, lon=77.2090)

    # 1. Raw GFS packet (Tier 4)
    raw_packet = EvidencePacket(
        id="gfs:test-001",
        source="gfs.point",
        authority_tier=4,
        provenance="live-recorded",
        issued_at=now,
        valid_from=now,
        valid_to=now + dt.timedelta(hours=24),
        place=place,
        values=[
            ValueItem(variable="temperature_2m", value=32.0, unit="°C", step=24),
            ValueItem(variable="precipitation", value=4.0, unit="mm", step=24),
        ],
        attribution="NOAA GFS",
    )

    corrected = apply_bias_correction_to_forecast(raw_packet, mos_model=mos_model, lead_time_hours=24)

    # Must remain model guidance (Tier 4) and carry model version & training window
    assert corrected.authority_tier == 4, "Corrected forecast must remain model guidance (Tier 4)"
    assert "MOS corrected" in corrected.source or "mos" in corrected.source.lower()
    assert "mos-india-v1.0" in corrected.attribution
    assert "2021-2024" in corrected.attribution

    # 2. Official IMD packet (Tier 2) must NEVER be altered or overridden
    official_packet = EvidencePacket(
        id="imd:official-001",
        source="imd.city_forecast",
        authority_tier=2,
        provenance="documented-sample",
        issued_at=now,
        valid_from=now,
        valid_to=now + dt.timedelta(hours=24),
        place=place,
        values=[
            ValueItem(variable="temperature_2m", value=28.0, unit="°C", step=24),
        ],
        attribution="India Meteorological Department (IMD)",
    )

    with pytest.raises(ValueError, match="Cannot apply MOS bias correction to official forecast"):
        apply_bias_correction_to_forecast(official_packet, mos_model=mos_model, lead_time_hours=24)
