from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.app.main import app


@pytest.mark.asyncio
async def test_aviation_metar_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/aviation/metar?station=VIDP")
        assert resp.status_code == 200
        data = resp.json()
        assert data["station"] == "VIDP"
        assert "raw" in data
        assert "flight_category" in data
        assert data["flight_category"] in ("VFR", "MVFR", "IFR", "LIFR")
        assert "wind_speed_kt" in data
        assert "temperature_c" in data
        # Check mandatory safety banner
        assert "INFORMATIONAL ONLY" in data["banner"]
        assert "DOES NOT constitute an official pre-flight briefing" in data["banner"]


@pytest.mark.asyncio
async def test_aviation_taf_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/v1/aviation/taf?station=VIDP")
        assert resp.status_code == 200
        data = resp.json()
        assert data["station"] == "VIDP"
        assert "raw" in data
        assert "summary" in data
        assert "INFORMATIONAL ONLY" in data["banner"]


@pytest.mark.asyncio
async def test_aviation_overview_and_crosswind_endpoint() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Overview
        resp = await client.get("/v1/aviation/overview?station=VIDP")
        assert resp.status_code == 200
        data = resp.json()
        assert data["station"] == "VIDP"
        assert len(data["runways"]) >= 1
        assert len(data["wind_calculations"]) >= 1
        assert "primary_runway_recommendation" in data
        assert "INFORMATIONAL ONLY" in data["banner"]

        # 2. Crosswind calculator direct endpoint
        cw_resp = await client.get(
            "/v1/aviation/crosswind?runway_heading=90&wind_dir=120&wind_speed=20&runway_name=RWY+09"
        )
        assert cw_resp.status_code == 200
        cw_data = cw_resp.json()
        assert cw_data["crosswind_kt"] == 10.0
        assert cw_data["crosswind_component_side"] == "right"
        assert cw_data["headwind_kt"] == 17.3


@pytest.mark.asyncio
async def test_aviation_caching_and_rate_limiting() -> None:
    from services.api.app.modules.aviation.adapter import AviationWeatherAdapter

    adapter = AviationWeatherAdapter(cache_ttl_seconds=60)
    # First call loads fixture / cache
    res1 = await adapter.get_metar("VIDP")
    assert res1["station"] == "VIDP"

    # Second call uses cache without external call
    res2 = await adapter.get_metar("VIDP")
    assert res2["is_cached"] is True


@pytest.mark.asyncio
async def test_smart_city_endpoints_workflow() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Heat index calculator endpoint
        hi_resp = await client.get("/v1/smart-city/heat-index?temp_c=36&rh_pct=65")
        assert hi_resp.status_code == 200
        hi_data = hi_resp.json()
        assert hi_data["heat_index_c"] > 40.0
        assert hi_data["category"] in ("Danger", "Extreme Danger")

        # 2. Register subscription
        sub_payload = {
            "subscriber_name": "Bangalore Smart City Ops",
            "place_id": "bengaluru",
            "webhook_url": "https://smartcity.bengaluru.gov.in/hooks/weather",
            "secret": "blore-key",
            "thresholds": {
                "heat_index_c": 38.0,
                "rain_rate_mm_hr": 10.0,
                "lightning_warning": True,
            },
            "cooldown_minutes": 10,
        }
        create_resp = await client.post("/v1/smart-city/subscriptions", json=sub_payload)
        assert create_resp.status_code == 201
        sub_info = create_resp.json()
        sub_id = sub_info["id"]

        # 3. List subscriptions
        list_resp = await client.get("/v1/smart-city/subscriptions?place_id=bengaluru")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 4. Evaluate observation with mock delivery
        eval_payload = {
            "place_id": "bengaluru",
            "temperature_c": 37.0,
            "relative_humidity_pct": 70.0,
            "rain_rate_mm_hr": 15.0,
            "lightning_detected": True,
        }
        eval_resp = await client.post("/v1/smart-city/evaluate", json=eval_payload)
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()
        assert eval_data["place_id"] == "bengaluru"
        assert eval_data["triggered_deliveries"] >= 1

        # 5. Check delivery logs
        deliv_resp = await client.get("/v1/smart-city/deliveries")
        assert deliv_resp.status_code == 200
        assert len(deliv_resp.json()) >= 1

        # 6. Delete subscription
        del_resp = await client.delete(f"/v1/smart-city/subscriptions/{sub_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True
