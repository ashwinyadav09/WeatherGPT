"""Unit tests for bias correction inference service and ForecastService post-hook (Ticket R11)."""
from __future__ import annotations

import datetime as dt

from ml.bias_correction.service import (
    apply_bias_correction_hook,
    find_nearest_training_station,
    haversine_km,
)
from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem


def _make_dummy_packet(place_name: str = "Delhi", lat: float = 28.5665, lon: float = 77.1031, temp: float = 35.0) -> EvidencePacket:
    now = dt.datetime(2024, 6, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    return EvidencePacket(
        id="test-pkt-1",
        source="Open-Meteo",
        authority_tier=4,
        provenance="live-recorded",
        issued_at=now,
        valid_from=now,
        valid_to=now + dt.timedelta(days=1),
        place=PlaceReference(id="delhi", name=place_name, lat=lat, lon=lon),
        values=[
            ValueItem(variable="temperature_max", value=temp, unit="°C"),
        ],
        attribution="Open-Meteo",
    )


def test_haversine_known_distance() -> None:
    # Delhi (VIDP: 28.5665, 77.1031) to Jaipur (VIJP: 26.8242, 75.8122) ~ 230 km
    dist = haversine_km(28.5665, 77.1031, 26.8242, 75.8122)
    assert 220.0 < dist < 245.0


def test_find_nearest_station() -> None:
    # Point very close to Delhi airport (within 10 km)
    st, dist = find_nearest_training_station(28.60, 77.15)
    assert st is not None
    assert st["id"] == "VIDP"
    assert dist < 15.0


def test_post_hook_raw_mode_returns_untouched() -> None:
    pkt = _make_dummy_packet()
    res = apply_bias_correction_hook([pkt], lat=28.5665, lon=77.1031, elev=237.0, ml_mode="raw")
    assert len(res) == 1
    assert res[0].values[0].value == 35.0


def test_post_hook_ml_mode_near_station_applies_correction() -> None:
    pkt = _make_dummy_packet()
    # At Delhi airport station (VIDP)
    res = apply_bias_correction_hook([pkt], lat=28.5665, lon=77.1031, elev=237.0, ml_mode="ml")
    # Should contain original packet + corrected packet
    assert len(res) == 2
    corrected_pkt = res[1]
    assert "MOS Bias Correction" in corrected_pkt.source

    var_map = {item.variable: item.value for item in corrected_pkt.values}
    assert "raw_value" in var_map
    assert "corrected_temperature_max" in var_map
    assert "p10" in var_map
    assert "p90" in var_map
    assert var_map["p10"] <= var_map["p90"]


def test_post_hook_far_location_falls_back_to_raw() -> None:
    pkt = _make_dummy_packet(place_name="Remote Ocean", lat=0.0, lon=80.0, temp=28.0)
    # Coordinates in central Indian Ocean > 500 km from any airport
    res = apply_bias_correction_hook([pkt], lat=0.0, lon=80.0, elev=0.0, ml_mode="ml")
    assert len(res) == 1
    assert res[0].values[0].value == 28.0


def test_post_hook_high_elevation_mismatch_falls_back_to_raw() -> None:
    pkt = _make_dummy_packet(place_name="Delhi Mountain", temp=20.0)
    # VIDP is at 237m; test elevation 1500m (diff > 300m)
    res = apply_bias_correction_hook([pkt], lat=28.5665, lon=77.1031, elev=1500.0, ml_mode="ml")
    assert len(res) == 1
    assert res[0].values[0].value == 20.0
