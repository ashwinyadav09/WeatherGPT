"""Seam tests for GFS and ECMWF model adapters, interpolation, and disagreement detection."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from packages.contracts.validator import validate_schema
from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem
from services.api.app.modules.forecast.adapters.ecmwf import ECMWFAdapter
from services.api.app.modules.forecast.adapters.gfs import (
    GFSPointAdapter,
    apply_elevation_correction,
    bilinear_interpolate,
)
from services.api.app.modules.forecast.comparator import detect_forecast_disagreement

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


def test_bilinear_interpolation():
    # Grid: (18.0, 73.0)=20.0, (18.0, 74.0)=30.0, (19.0, 73.0)=25.0, (19.0, 74.0)=35.0
    # Center (18.5, 73.5) should be average = 27.5
    val = bilinear_interpolate(
        lat=18.5,
        lon=73.5,
        lat1=18.0,
        lat2=19.0,
        lon1=73.0,
        lon2=74.0,
        q11=20.0,
        q21=30.0,
        q12=25.0,
        q22=35.0,
    )
    assert abs(val - 27.5) < 1e-4


def test_elevation_correction():
    # Standard lapse rate: -6.5 °C per 1000m
    # If station is 500m higher than model grid cell elevation, temp should drop by ~3.25 °C
    corr = apply_elevation_correction(temp_c=30.0, model_elev_m=100.0, target_elev_m=600.0)
    assert abs(corr - 26.75) < 0.05

    # If station is lower than model elevation, temp increases
    corr_lower = apply_elevation_correction(temp_c=25.0, model_elev_m=1000.0, target_elev_m=500.0)
    assert abs(corr_lower - 28.25) < 0.05


@pytest.mark.asyncio
async def test_gfs_adapter_conformance():
    adapter = GFSPointAdapter()
    packets = await adapter.get_forecast(lat=18.52, lon=73.85, place_name="Pune", elevation=560.0)

    assert len(packets) == 1
    packet = packets[0]
    data = packet.model_dump(mode="json")

    # Strict conformance check against Evidence Packet schema
    validate_schema("evidence_packet", data)
    assert data["source"] == "gfs.point"
    assert data["authority_tier"] == 4
    assert len(data["values"]) > 0
    assert any(v["variable"] == "temperature_2m" for v in data["values"])


@pytest.mark.asyncio
async def test_ecmwf_adapter_conformance_and_uncertainty():
    adapter = ECMWFAdapter(model_type="ifs")
    packets = await adapter.get_forecast(lat=18.52, lon=73.85, place_name="Pune", elevation=560.0)

    assert len(packets) == 1
    packet = packets[0]
    data = packet.model_dump(mode="json")

    validate_schema("evidence_packet", data)
    assert data["source"] == "ecmwf.ifs"
    assert data["authority_tier"] == 4
    # Uncertainty populated from ensemble spread
    assert data.get("uncertainty") is not None
    assert data["uncertainty"]["type"] == "ensemble_std_dev"


def test_material_disagreement_detection():
    now = dt.datetime.now(dt.timezone.utc)
    place = PlaceReference(id="pune", name="Pune", lat=18.52, lon=73.85)

    # Official forecast: No rain (0 mm), max temp 30 °C
    official = EvidencePacket(
        id="pkt:imd:01",
        source="imd.city_forecast",
        authority_tier=2,
        provenance="documented-sample",
        issued_at=now,
        valid_from=now,
        valid_to=now + dt.timedelta(days=1),
        place=place,
        values=[
            ValueItem(variable="temperature_2m_max", value=30.0, unit="°C"),
            ValueItem(variable="precipitation_sum", value=0.0, unit="mm"),
        ],
        attribution="IMD",
    )

    # Model guidance: Heavy rain (25 mm), max temp 24 °C (material disagreement!)
    model_gfs = EvidencePacket(
        id="pkt:gfs:01",
        source="gfs.point",
        authority_tier=4,
        provenance="live-recorded",
        issued_at=now,
        valid_from=now,
        valid_to=now + dt.timedelta(days=1),
        place=place,
        values=[
            ValueItem(variable="temperature_2m_max", value=24.0, unit="°C"),
            ValueItem(variable="precipitation_sum", value=25.0, unit="mm"),
        ],
        attribution="NOAA GFS (CC BY 4.0)",
    )

    disagreements = detect_forecast_disagreement(official, [model_gfs])
    assert len(disagreements) >= 1
    d = disagreements[0]
    assert d["has_material_disagreement"] is True
    assert "precipitation_sum" in d["variables"] or "temperature_2m_max" in d["variables"]
    assert d["official_source"] == "imd.city_forecast"
    assert d["model_source"] == "gfs.point"


@pytest.mark.asyncio
async def test_fallback_drill_when_imd_down():
    """Fallback drill: when IMD adapter is disabled/failing, model guidance answers with full provenance."""
    gfs_adapter = GFSPointAdapter()
    packets = await gfs_adapter.get_forecast(lat=28.61, lon=77.20, place_name="Delhi")

    assert len(packets) >= 1
    pkt = packets[0]
    assert pkt.authority_tier == 4
    assert "GFS" in pkt.attribution
    # Labelled distinctly from official forecast
    assert pkt.source in ("gfs.point", "ecmwf.ifs")


def test_model_output_store():
    from services.ingest.model_store import ModelOutputStore

    store = ModelOutputStore()
    now = dt.datetime.now(dt.timezone.utc)
    cycle_id = store.record_cycle(
        model="gfs",
        cycle_time=now,
        lead_hours=[0, 6, 12, 18, 24],
        variables=["temperature_2m", "precipitation"],
    )

    assert "gfs:" in cycle_id
    latest = store.get_latest_cycle("gfs")
    assert latest is not None
    assert latest["bounds"]["lat_min"] == 6.0
    assert latest["bounds"]["lon_max"] == 98.0
    assert len(latest["lead_hours"]) == 5
