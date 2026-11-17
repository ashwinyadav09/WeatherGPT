"""Build documented IMD API fixtures modelled on published IMD API reference samples."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMD_DIR = ROOT / "eval" / "fixtures" / "imd"
IMD_DIR.mkdir(parents=True, exist_ok=True)

# 1. District Nowcast
nowcast_district = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#nowcast-district",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "district_id": "356.27.521",
    "district_name": "PUNE",
    "state_name": "MAHARASHTRA",
    "issue_time": "2026-11-17 14:30:00 IST",
    "valid_until": "2026-11-17 17:30:00 IST",
    "colour_code": "2",
    "colour_name": "Yellow",
    "hazard_code": "TS_RA",
    "hazard_name": "Thunderstorm with light to moderate rain",
    "warning_text": "Thunderstorm accompanied with lightning and light to moderate spells of rain very likely to occur at isolated places in the district during next 3 hours."
}

# 2. Station Nowcast
nowcast_station = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#nowcast-station",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "station_id": "43063",
    "station_name": "PUNE SHIVAJINAGAR",
    "issue_time": "2026-11-17 15:00:00 IST",
    "valid_until": "2026-11-17 18:00:00 IST",
    "warning_level": 2,
    "phenomenon": "LIGHT RAIN",
    "wind_speed_gust": "35 kmph"
}

# 3. District Warnings (5 days)
warnings_district = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#district-warnings",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "district_code": "521",
    "district_name": "PUNE",
    "state": "MAHARASHTRA",
    "date_issued": "2026-11-17",
    "warnings": [
        {"day": 1, "date": "2026-11-17", "colour": "Yellow", "code": 3, "warning": "Thunderstorm with lightning"},
        {"day": 2, "date": "2026-11-18", "colour": "Green", "code": 4, "warning": "No warning"},
        {"day": 3, "date": "2026-11-19", "colour": "Green", "code": 4, "warning": "No warning"},
        {"day": 4, "date": "2026-11-20", "colour": "Green", "code": 4, "warning": "No warning"},
        {"day": 5, "date": "2026-11-21", "colour": "Green", "code": 4, "warning": "No warning"}
    ]
}

# 4. Sub-division Warnings
warnings_subdivision = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#subdivision-warnings",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "subdivision_id": "14",
    "subdivision_name": "MADHYA MAHARASHTRA",
    "issue_date": "2026-11-17",
    "day1_warning": "Isolated thunderstorm with lightning",
    "day1_colour": "YELLOW",
    "day2_warning": "Nil",
    "day2_colour": "GREEN"
}

# 5. AWS Observation
aws_observation = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#aws-data",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "station_id": "PUN01",
    "station_name": "PUNE-AGRICULTURE_COLLEGE",
    "latitude": 18.53,
    "longitude": 73.85,
    "timestamp_utc": "2026-11-17T08:30:00Z",
    "temperature_c": 28.6,
    "humidity_pct": 58,
    "wind_speed_kmph": 8.5,
    "wind_dir_deg": 240,
    "rain_fall_last_hour_mm": 0.0,
    "pressure_hpa": 952.1
}

# 6. ARG Observation
arg_observation = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#arg-data",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "station_id": "ARG_HAVELI",
    "station_name": "HAVELI",
    "district": "PUNE",
    "timestamp_utc": "2026-11-17T08:30:00Z",
    "rainfall_today_mm": 1.5,
    "battery_v": 12.4
}

# 7. Current Weather
current_weather = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#current-weather",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "station_code": "VAPO",
    "station_name": "PUNE",
    "observed_at": "2026-11-17 14:00 IST",
    "temp_c": 29.2,
    "rh": 54,
    "wind_dir": "WNW",
    "wind_speed_knots": 6,
    "weather_desc": "Partly cloudy",
    "visibility_km": 6.0
}

# 8. Mausamgram
mausamgram = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#mausamgram",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "lat": 18.52,
    "lon": 73.86,
    "model": "WRF-IMD 3km",
    "run_time": "2026-11-17T00:00:00Z",
    "steps": [
        {"step_hour": 3, "valid_utc": "2026-11-17T03:00:00Z", "temp_2m": 24.1, "rain_accum_mm": 0.0, "rh": 72},
        {"step_hour": 6, "valid_utc": "2026-11-17T06:00:00Z", "temp_2m": 28.5, "rain_accum_mm": 0.0, "rh": 55},
        {"step_hour": 9, "valid_utc": "2026-11-17T09:00:00Z", "temp_2m": 29.8, "rain_accum_mm": 0.2, "rh": 50},
        {"step_hour": 12, "valid_utc": "2026-11-17T12:00:00Z", "temp_2m": 26.4, "rain_accum_mm": 1.8, "rh": 68}
    ]
}

# 9. River Basin QPF
river_basin_qpf = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#river-basin-qpf",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "basin_name": "KRISHNA",
    "sub_basin": "UPPER KRISHNA",
    "issue_date": "2026-11-17",
    "qpf_day1": "0.1 - 10.0 mm",
    "qpf_day2": "0.0 mm",
    "qpf_day3": "0.0 mm"
}

# 10. Port Warning
port_warning = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#port-warning",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "port_name": "MUMBAI",
    "signal_number": "LC-III",
    "signal_name": "Local Cautionary Signal No. 3",
    "issue_time": "2026-11-17 11:30 IST",
    "description": "Squally weather with wind speed 40-50 kmph gusting to 60 kmph likely over sea off Maharashtra coast."
}

# 11. Sea Area Bulletin
sea_area_bulletin = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#sea-area-bulletin",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "sea_area": "EAST CENTRAL ARABIAN SEA",
    "bulletin_time": "2026-11-17 12:00 UTC",
    "synoptic_situation": "Trough of low pressure at mean sea level over south Konkan.",
    "wind": "Northwesterly to Westerly 15 to 20 knots gusting to 25 knots in showers.",
    "weather": "Fairly widespread rain or thundershowers.",
    "visibility": "Moderate becoming poor in rain.",
    "sea_condition": "Moderate."
}

# 12. Fishermen Warning
fishermen_warning = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#fishermen-warning",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "coast": "North Maharashtra Coast",
    "valid_for": "Next 5 days",
    "warning_issued": "No warning for fishermen along North Maharashtra coast for days 1 to 5.",
    "deep_sea_warning": "Fishermen advised not to venture into Andaman Sea and adjoining Southeast Bay of Bengal on Day 1."
}

# 13. Cyclone Track
cyclone_track = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#cyclone-track",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "cyclone_name": "SAMPLE-STORM",
    "intensity": "Severe Cyclonic Storm",
    "basin": "Bay of Bengal",
    "bulletin_no": "04",
    "time_utc": "2026-11-17T06:00:00Z",
    "center_lat": 16.2,
    "center_lon": 86.5,
    "estimated_central_pressure_hpa": 988,
    "max_sustained_wind_speed_knots": 55,
    "track_points": [
        {"time_utc": "2026-11-17T12:00:00Z", "lat": 16.8, "lon": 86.8, "stage": "SCS", "max_wind_knots": 60},
        {"time_utc": "2026-11-18T00:00:00Z", "lat": 17.9, "lon": 87.2, "stage": "VSCS", "max_wind_knots": 70},
        {"time_utc": "2026-11-18T12:00:00Z", "lat": 19.1, "lon": 87.5, "stage": "VSCS", "max_wind_knots": 75}
    ]
}

# 14. Sun & Moon
sun_moon = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#sun-moon",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "place": "PUNE",
    "date": "2026-11-18",
    "sunrise": "06:42 IST",
    "sunset": "17:58 IST",
    "moonrise": "14:15 IST",
    "moonset": "02:10 IST"
}

# 15. Highway Nowcast
highway_nowcast = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#highway-nowcast",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "highway_no": "NH-48",
    "stretch": "Mumbai - Pune Expressway",
    "issue_time": "2026-11-17 14:00 IST",
    "valid_until": "2026-11-17 18:00 IST",
    "condition": "Light rain and wet surface near Khandala Ghat. Caution advised due to slippery road."
}

# 16. Agromet Advisory
agromet_advisory = {
    "_provenance": "documented-sample",
    "_source": "https://api.imd.gov.in/public/api_reference.html#agromet",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "state": "Maharashtra",
    "district": "Pune",
    "bulletin_date": "2026-11-17",
    "crop_advisories": [
        {
            "crop": "Sugarcane",
            "stage": "Vegetative",
            "advisory": "Maintain adequate moisture; irrigate if soil shows dryness."
        },
        {
            "crop": "Gram / Chickpea",
            "stage": "Sowing",
            "advisory": "Complete rabi chickpea sowing using certified seed treated with Trichoderma."
        }
    ]
}

# 17. Seasonal Forecast (Spec-only)
seasonal_forecast = {
    "_provenance": "spec-only",
    "_source": "https://api.imd.gov.in/public/api_reference.html#seasonal-forecast",
    "_recorded_at": "2026-11-17T06:00:00Z",
    "season": "Post-Monsoon (OND)",
    "year": 2026,
    "forecast_zone": "South Peninsular India",
    "category": "Normal to Above Normal",
    "probability_pct": {
        "above_normal": 45,
        "normal": 35,
        "below_normal": 20
    }
}

ALL_IMD = {
    "nowcast_district_sample.json": nowcast_district,
    "nowcast_station_sample.json": nowcast_station,
    "warnings_district_sample.json": warnings_district,
    "warnings_subdivision_sample.json": warnings_subdivision,
    "aws_observation_sample.json": aws_observation,
    "arg_observation_sample.json": arg_observation,
    "current_weather_sample.json": current_weather,
    "mausamgram_sample.json": mausamgram,
    "river_basin_qpf_sample.json": river_basin_qpf,
    "port_warning_sample.json": port_warning,
    "sea_area_bulletin_sample.json": sea_area_bulletin,
    "fishermen_warning_sample.json": fishermen_warning,
    "cyclone_track_sample.json": cyclone_track,
    "sun_moon_sample.json": sun_moon,
    "highway_nowcast_sample.json": highway_nowcast,
    "agromet_advisory_sample.json": agromet_advisory,
    "seasonal_forecast_sample.json": seasonal_forecast,
}

for fname, data in ALL_IMD.items():
    (IMD_DIR / fname).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote IMD fixture: {fname}")

print(f"Total IMD fixtures created: {len(ALL_IMD)}")
