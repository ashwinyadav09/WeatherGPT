"""Seam tests for Point-Forecast Bias Correction (Ticket 16)."""

from __future__ import annotations

import datetime as dt

import pytest

from ml.bias_correction.dataset import get_dataset_manifest, load_time_split_dataset
from ml.bias_correction.mos_model import PointForecastMOSModel
from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem
from services.api.app.modules.forecast.bias_corrector import apply_bias_correction_to_forecast


@pytest.fixture
def mos_model() -> PointForecastMOSModel:
    model = PointForecastMOSModel()
    model.train()
    return model


def test_time_split_dataset_and_licences():
    train_data, val_data, test_data = load_time_split_dataset()
    manifest = get_dataset_manifest()

    # Verify time-split without leakage
    assert len(train_data) > 0, "Training set must contain data"
    assert len(val_data) > 0, "Validation set must contain data"
    assert len(test_data) > 0, "Test set must contain data"

    max_train_date = max(d["date"] for d in train_data)
    min_val_date = min(d["date"] for d in val_data)
    max_val_date = max(d["date"] for d in val_data)
    min_test_date = min(d["date"] for d in test_data)

    assert max_train_date < min_val_date, "Training data must precede validation data in time"
    assert max_val_date < min_test_date, "Validation data must precede test data in time"

    # Verify recorded licences in manifest
    assert "open_meteo" in manifest
    assert "iem_metar" in manifest
    assert "gfs_archive" in manifest
    assert manifest["open_meteo"]["licence"] == "CC BY 4.0"
    assert "open" in manifest["iem_metar"]["licence"].lower()


def test_temperature_mos_evaluation_vs_baselines(mos_model: PointForecastMOSModel):
    report = mos_model.evaluate_temperature()

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

    # MOS must reduce MAE over raw model, persistence and climatology
    assert mos_mae < raw_mae, f"MOS MAE ({mos_mae}) must beat raw model ({raw_mae})"
    assert mos_mae < persist_mae, f"MOS MAE ({mos_mae}) must beat persistence ({persist_mae})"
    assert mos_mae < clim_mae, f"MOS MAE ({mos_mae}) must beat climatology ({clim_mae})"
    assert report["mos"]["rmse"] < report["raw_model"]["rmse"]


def test_rain_event_metrics_and_reliability_diagram(mos_model: PointForecastMOSModel):
    rain_report = mos_model.evaluate_precipitation()

    # Must report POD, FAR, CSI for rain event threshold (e.g. >= 2.5 mm)
    assert "pod" in rain_report["mos"]
    assert "far" in rain_report["mos"]
    assert "csi" in rain_report["mos"]

    mos_csi = rain_report["mos"]["csi"]
    raw_csi = rain_report["raw_model"]["csi"]
    print(f"\nRain Event CSI: MOS={mos_csi:.3f}, Raw={raw_csi:.3f}")

    # MOS Critical Success Index must beat raw model thresholding
    assert mos_csi > raw_csi, f"MOS CSI ({mos_csi}) must beat raw model ({raw_csi})"

    # Reliability diagram calibration bins
    diagram = mos_model.generate_reliability_diagram()
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

    # At distant lead times (e.g., 240h / 10 days) where statistical correction lacks skill over raw model,
    # gate policy must safely reject correction and fall back to raw model
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
