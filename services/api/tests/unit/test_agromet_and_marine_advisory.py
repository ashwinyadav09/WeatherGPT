from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.api.app.conversation.agent import ChatRequest, ConversationAgent
from services.api.app.modules.advisory.agromet import AgrometAdapter
from services.api.app.modules.advisory.marine import MarineAdapter

ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = ROOT / "eval" / "fixtures" / "imd"


def test_agromet_and_marine_fixtures_provenance():
    """Verify that agromet and marine fixtures exist and have documented-sample provenance."""
    agro_path = FIXTURES_DIR / "agromet_advisory_sample.json"
    marine_path = FIXTURES_DIR / "marine_bulletin_sample.json"

    assert agro_path.exists(), "agromet_advisory_sample.json missing"
    assert marine_path.exists(), "marine_bulletin_sample.json missing"

    with agro_path.open("r", encoding="utf-8") as f:
        agro_data = json.load(f)
    assert agro_data.get("_provenance") == "documented-sample"
    assert "https://api.imd.gov.in" in agro_data.get("_source", "")
    assert "districts" in agro_data
    assert "ludhiana" in agro_data["districts"]
    assert "wheat" in agro_data["districts"]["ludhiana"]["crops"]
    assert "rice" in agro_data["districts"]["ludhiana"]["crops"]

    with marine_path.open("r", encoding="utf-8") as f:
        marine_data = json.load(f)
    assert marine_data.get("_provenance") == "documented-sample"
    assert "https://api.imd.gov.in" in marine_data.get("_source", "")
    assert "areas" in marine_data
    assert "konkan_goa" in marine_data["areas"]
    assert "safety_banner" in marine_data


@pytest.mark.asyncio
async def test_agromet_advisory_wheat_and_rice_stages():
    """Verify farmer can query wheat or rice growth stages and receive cited IMD agromet advice."""
    adapter = AgrometAdapter()

    # 1. Wheat at Sowing stage in Ludhiana
    res_wheat_sow = await adapter.get_agromet_advisory(
        district="Ludhiana",
        crop="wheat",
        stage="sowing",
        language="en",
    )
    assert res_wheat_sow["status"] == "success"
    assert res_wheat_sow["crop"] == "wheat"
    assert "sowing" in res_wheat_sow["stage"].lower()
    assert "sowing window" in res_wheat_sow["advisory_text"].lower()
    assert "India Meteorological Department (IMD)" in res_wheat_sow["source"]
    assert "GKMS" in res_wheat_sow["source"] or "Gramin Krishi Mausam Sewa" in res_wheat_sow["source"]

    # 2. Wheat at Crown Root Initiation (CRI) in Hindi
    res_wheat_cri_hi = await adapter.get_agromet_advisory(
        district="Ludhiana",
        crop="गेहूं",
        stage="CRI",
        language="hi",
    )
    assert res_wheat_cri_hi["status"] == "success"
    assert "सिंचाई" in res_wheat_cri_hi["advisory_text"]
    assert "IMD" in res_wheat_cri_hi["source"] or "मौसम विज्ञान विभाग" in res_wheat_cri_hi["source"]

    # 3. Rice at Flowering stage in Varanasi
    res_rice_flowering = await adapter.get_agromet_advisory(
        district="Varanasi",
        crop="rice",
        stage="flowering",
        language="en",
    )
    assert res_rice_flowering["status"] == "success"
    assert res_rice_flowering["crop"] == "rice"
    assert "moisture" in res_rice_flowering["advisory_text"].lower()

    # 4. Rice at Maturity/Harvesting stage in Burdwan
    res_rice_harvest_hi = await adapter.get_agromet_advisory(
        district="Burdwan",
        crop="धान",
        stage="कटाई",
        language="hi",
    )
    assert res_rice_harvest_hi["status"] == "success"
    assert ("कटाई" in res_rice_harvest_hi["advisory_text"] or "पानी" in res_rice_harvest_hi["advisory_text"])


@pytest.mark.asyncio
async def test_agromet_never_gives_pesticide_doses():
    """Verify that asking for pesticide doses via agromet advisory triggers refusal and KVK redirect."""
    adapter = AgrometAdapter()

    dosage_queries = [
        ("wheat", "pesticide dose for yellow rust", "How much spray dose per acre?"),
        ("rice", "कीटनाशक की मात्रा", "धान में कितनी दवा का छिड़काव करें?"),
    ]

    for crop, stage, q_text in dosage_queries:
        res = await adapter.get_agromet_advisory(
            district="Ludhiana",
            crop=crop,
            stage=stage,
            query_text=q_text,
            language="en" if "pesticide" in q_text else "hi",
        )
        assert res["status"] == "refused_pesticide_dose"
        assert res["pesticide_refusal"] is True
        assert "1800-180-1551" in str(res)
        assert ("KVK" in str(res) or "कृषि विज्ञान केंद्र" in str(res) or "Kisan Call Centre" in str(res))
        # Ensure no dosage units are returned
        assert "ml/acre" not in str(res).lower()
        assert "kg/ha" not in str(res).lower()


@pytest.mark.asyncio
async def test_marine_bulletin_and_fishermen_warnings():
    """Verify coastal marine bulletins and fishermen warnings carry official safety notice."""
    adapter = MarineAdapter()

    # 1. Konkan-Goa coast (Active warning)
    res_konkan = await adapter.get_marine_bulletin(area="konkan", language="en")
    assert res_konkan["status"] == "success"
    assert "Konkan-Goa" in res_konkan["area_name"]
    assert res_konkan["sea_condition"] in ("Rough", "Very Rough", "Rough to Very Rough")
    assert res_konkan["fishermen_warning"]["status"] == "warning_active"
    assert "NOT to venture" in res_konkan["fishermen_warning"]["warning_en"]
    # Check mandatory safety notice
    assert "SAFETY NOTICE" in res_konkan["safety_banner"]["text_en"]
    assert "INCOIS" in res_konkan["safety_banner"]["text_en"]
    assert "IMD" in res_konkan["safety_banner"]["text_en"]

    # 2. North Gujarat coast (No warning)
    res_gujarat = await adapter.get_marine_bulletin(area="north gujarat", language="hi")
    assert res_gujarat["status"] == "success"
    assert res_gujarat["fishermen_warning"]["status"] == "no_warning"
    assert "सुरक्षा सूचना" in res_gujarat["safety_banner"]["text_hi"]

    # 3. Tamil Nadu coast (Orange level warning)
    res_tn = await adapter.get_marine_bulletin(area="tamil nadu", language="en")
    assert res_tn["status"] == "success"
    assert res_tn["fishermen_warning"]["level"] in ("orange", "red")
    assert "Gulf of Mannar" in res_tn["fishermen_warning"]["warning_en"]


@pytest.mark.asyncio
async def test_conversation_scenario_wheat_farmer():
    """Scenario test: Farmer asks for wheat sowing advisory in Ludhiana."""
    agent = ConversationAgent()
    req = ChatRequest(
        session_id="wheat_scenario_1",
        text="What is the agromet advisory for wheat sowing in Ludhiana?",
        language="en",
        stream=False,
    )
    tokens: list[str] = []
    card_data: dict | None = None
    async for ev in agent.run_chat(req):
        if ev["event"] == "token":
            tokens.append(ev["data"]["text"])
        elif ev["event"] == "card":
            card_data = ev["data"]

    full_text = "".join(tokens)
    assert card_data is not None
    assert "IMD Agromet" in card_data["headline"]
    assert "Wheat" in card_data["headline"]
    assert "Sowing" in card_data["headline"]
    assert "GKMS" in card_data["source_line"] or "IMD" in card_data["source_line"]
    assert "sowing window" in full_text.lower()
    # Refusal reminder present
    assert "1800-180-1551" in str(card_data)


@pytest.mark.asyncio
async def test_conversation_scenario_rice_farmer_hindi():
    """Scenario test: Farmer asks in Hindi for rice flowering stage advisory in Varanasi."""
    agent = ConversationAgent()
    req = ChatRequest(
        session_id="rice_scenario_hi",
        text="वाराणसी में धान की फसल के लिए मौसम आधारित सलाह क्या है?",
        language="hi",
        stream=False,
    )
    tokens: list[str] = []
    card_data: dict | None = None
    async for ev in agent.run_chat(req):
        if ev["event"] == "token":
            tokens.append(ev["data"]["text"])
        elif ev["event"] == "card":
            card_data = ev["data"]

    full_text = "".join(tokens)
    assert card_data is not None
    assert "कृषि सलाह" in card_data["headline"] or "धान" in card_data["headline"]
    assert "मौसम विज्ञान विभाग" in card_data["source_line"] or "IMD" in card_data["source_line"] or "GKMS" in card_data["source_line"]
    assert len(full_text) > 10


@pytest.mark.asyncio
async def test_conversation_scenario_coastal_fisherman_marine_warning():
    """Scenario test: Fisherman asks about sea conditions and warnings along Konkan coast."""
    agent = ConversationAgent()
    req = ChatRequest(
        session_id="marine_scenario_1",
        text="What is the sea condition and fishermen warning for Konkan coast?",
        language="en",
        stream=False,
    )
    tokens: list[str] = []
    card_data: dict | None = None
    async for ev in agent.run_chat(req):
        if ev["event"] == "token":
            tokens.append(ev["data"]["text"])
        elif ev["event"] == "card":
            card_data = ev["data"]

    full_text = "".join(tokens)
    assert card_data is not None
    assert "Coastal Bulletin" in card_data["headline"]
    assert "Konkan" in card_data["headline"]
    assert "SAFETY NOTICE" in card_data["caveat"]
    assert "INCOIS" in card_data["caveat"]
    assert "NOT to venture" in full_text

