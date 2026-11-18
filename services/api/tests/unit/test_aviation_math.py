from __future__ import annotations

from services.api.app.modules.aviation.decoder import (
    calculate_flight_category,
    calculate_wind_components,
    decode_metar_raw,
)


def test_flight_category_calculations() -> None:
    # 1. VFR: Visibility > 8000m and Ceiling > 3000ft (or None)
    assert calculate_flight_category(visibility_meters=10000, ceiling_ft=None) == "VFR"
    assert calculate_flight_category(visibility_meters=9000, ceiling_ft=4000) == "VFR"

    # 2. MVFR: Visibility 5000-8000m or Ceiling 1000-3000ft
    assert calculate_flight_category(visibility_meters=6000, ceiling_ft=None) == "MVFR"
    assert calculate_flight_category(visibility_meters=10000, ceiling_ft=2500) == "MVFR"
    assert calculate_flight_category(visibility_meters=7000, ceiling_ft=1500) == "MVFR"

    # 3. IFR: Visibility 1600-<5000m or Ceiling 500-<1000ft
    assert calculate_flight_category(visibility_meters=4000, ceiling_ft=None) == "IFR"
    assert calculate_flight_category(visibility_meters=10000, ceiling_ft=800) == "IFR"
    assert calculate_flight_category(visibility_meters=3000, ceiling_ft=600) == "IFR"

    # 4. LIFR: Visibility < 1600m or Ceiling < 500ft
    assert calculate_flight_category(visibility_meters=800, ceiling_ft=None) == "LIFR"
    assert calculate_flight_category(visibility_meters=10000, ceiling_ft=200) == "LIFR"
    assert calculate_flight_category(visibility_meters=500, ceiling_ft=100) == "LIFR"

    # 5. Most restrictive rule: Good ceiling (4000ft) but poor visibility (3000m) -> IFR
    assert calculate_flight_category(visibility_meters=3000, ceiling_ft=4000) == "IFR"
    # Good visibility (10000m) but LIFR ceiling (300ft) -> LIFR
    assert calculate_flight_category(visibility_meters=10000, ceiling_ft=300) == "LIFR"


def test_crosswind_hand_checked_worked_examples() -> None:
    # Example 1: Runway 09 (090° heading), Wind 120° at 20 kt
    # Angle diff = 120 - 90 = 30°
    # sin(30°) = 0.5 -> Crosswind = 10.0 kt (from right)
    # cos(30°) = 0.8660 -> Headwind = 17.3 kt
    calc1 = calculate_wind_components("RWY 09", 90, 120, 20.0)
    assert calc1.crosswind_kt == 10.0
    assert calc1.crosswind_component_side == "right"
    assert calc1.headwind_kt == 17.3
    assert calc1.is_tailwind is False

    # Example 2: Runway 27 (270° heading), Wind 240° at 16 kt
    # Angle diff = 240 - 270 = -30°
    # |sin(-30°)| = 0.5 -> Crosswind = 8.0 kt (from left)
    # cos(-30°) = 0.8660 -> Headwind = 13.9 kt
    calc2 = calculate_wind_components("RWY 27", 270, 240, 16.0)
    assert calc2.crosswind_kt == 8.0
    assert calc2.crosswind_component_side == "left"
    assert calc2.headwind_kt == 13.9
    assert calc2.is_tailwind is False

    # Example 3: Runway 09 (090° heading), Wind 270° at 10 kt (Direct tailwind)
    # Angle diff = 180°
    # sin(180°) = 0 -> Crosswind = 0.0 kt
    # cos(180°) = -1.0 -> Headwind = -10.0 kt (Tailwind)
    calc3 = calculate_wind_components("RWY 09", 90, 270, 10.0)
    assert calc3.crosswind_kt == 0.0
    assert calc3.headwind_kt == -10.0
    assert calc3.is_tailwind is True

    # Example 4: Direct Crosswind - Runway 36 (360° heading), Wind 090° at 15 kt
    # Angle diff = 90° -> Crosswind = 15.0 kt (from right), Headwind = 0.0 kt
    calc4 = calculate_wind_components("RWY 36", 360, 90, 15.0)
    assert calc4.crosswind_kt == 15.0
    assert calc4.crosswind_component_side == "right"
    assert calc4.headwind_kt == 0.0
    assert calc4.is_tailwind is False

    # Example 5: Calm wind (0 kt)
    calc5 = calculate_wind_components("RWY 10", 100, None, 0.0)
    assert calc5.crosswind_kt == 0.0
    assert calc5.headwind_kt == 0.0
    assert calc5.crosswind_component_side == "calm"


def test_decode_metar_raw_syntax() -> None:
    # Test Delhi Indira Gandhi METAR
    raw_vidp = "METAR VIDP 171200Z 27014KT 4000 HZ NSC 28/14 Q1012 NOSIG="
    dec_vidp = decode_metar_raw(raw_vidp)
    assert dec_vidp["station"] == "VIDP"
    assert dec_vidp["wind_dir"] == 270
    assert dec_vidp["wind_speed_kt"] == 14.0
    assert dec_vidp["visibility_meters"] == 4000
    assert "Haze" in dec_vidp["weather_conditions"]
    assert dec_vidp["temperature_c"] == 28.0
    assert dec_vidp["dewpoint_c"] == 14.0
    assert dec_vidp["qnh_hpa"] == 1012.0
    assert dec_vidp["flight_category"] == "IFR"  # 4000m is IFR

    # Test Mumbai Chhatrapati Shivaji METAR with gusts and ceiling
    raw_vabb = "METAR VABB 171200Z 24016G24KT 3000 -RA BKN015 OVC030 29/25 Q1008 TEMPO 1500 TSRA="
    dec_vabb = decode_metar_raw(raw_vabb)
    assert dec_vabb["station"] == "VABB"
    assert dec_vabb["wind_dir"] == 240
    assert dec_vabb["wind_speed_kt"] == 16.0
    assert dec_vabb["wind_gust_kt"] == 24.0
    assert dec_vabb["visibility_meters"] == 3000
    assert "Light Rain" in dec_vabb["weather_conditions"]
    assert dec_vabb["ceiling_ft"] == 1500  # Lowest BKN layer
    assert dec_vabb["flight_category"] == "IFR"
