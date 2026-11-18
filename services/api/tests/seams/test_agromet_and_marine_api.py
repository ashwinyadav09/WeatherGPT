from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from services.api.app.main import app


@pytest.mark.asyncio
async def test_agromet_api_endpoint():
    """Verify GET /v1/advisory/agromet returns valid cited advisory data."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/v1/advisory/agromet?district=Ludhiana&crop=wheat&stage=sowing&language=en")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["crop"] == "wheat"
        assert "sowing window" in data["advisory_text"].lower()
        assert "IMD" in data["source"] or "GKMS" in data["source"]
        assert "provenance" in data


@pytest.mark.asyncio
async def test_agromet_api_pesticide_refusal():
    """Verify GET /v1/advisory/agromet refuses pesticide dosages and returns KVK redirect."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            "/v1/advisory/agromet?district=Ludhiana&crop=wheat&stage=pesticide_dose&query_text=spray%20dose%20per%20acre"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "refused_pesticide_dose"
        assert data["pesticide_refusal"] is True
        assert "1800-180-1551" in data["helplines"]
        assert "KVK" in data["message"] or "Kisan Call Centre" in data["message"]


@pytest.mark.asyncio
async def test_marine_api_endpoint():
    """Verify GET /v1/advisory/marine returns coastal bulletin with mandatory safety notice."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/v1/advisory/marine?area=konkan&language=en")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "Konkan-Goa" in data["area_name"]
        assert "safety_banner" in data
        assert "SAFETY NOTICE" in data["safety_banner"]["text_en"]
        assert "fishermen_warning" in data


@pytest.mark.asyncio
async def test_advisory_general_endpoint_with_agro_and_marine_domains():
    """Verify GET /v1/advisory supports agro and marine domains cleanly."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Agro domain
        res_agro = await client.get("/v1/advisory?place_id=Ludhiana&domain=agro&crop=rice&stage=nursery")
        assert res_agro.status_code == 200
        agro_cards = res_agro.json()
        assert len(agro_cards) == 1
        assert agro_cards[0]["domain"] == "agro"
        assert "agromet_data" in agro_cards[0]

        # Marine domain
        res_marine = await client.get("/v1/advisory?place_id=konkan&domain=marine")
        assert res_marine.status_code == 200
        marine_cards = res_marine.json()
        assert len(marine_cards) == 1
        assert marine_cards[0]["domain"] == "marine"
        assert "marine_data" in marine_cards[0]
