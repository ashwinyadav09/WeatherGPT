"""Unit tests for Tier-1 and Tier-2 languages (Ticket R1.3).

Requirements:
- config/languages.yaml: Tier 1 = en, hi, bn, mr, te, ta, or. Tier 2 = gu, kn, ml, pa, as (smoke-tested only).
- Language selection: the UI selector is the source of truth. "auto" uses script detection, then simple stopword heuristics to separate Hindi from Marathi.
- Odia templates and glossary entries exist in seeds/.
- Every Tier-1 language has templates, glossary, and UI strings; a test iterates over them.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from services.api.app.conversation.agent import ChatRequest, ConversationAgent
from services.api.app.conversation.i18n import detect_language

ROOT = Path(__file__).resolve().parents[4]
TIER1_LANGUAGES = ["en", "hi", "bn", "mr", "te", "ta", "or"]
TIER2_LANGUAGES = ["gu", "kn", "ml", "pa", "as"]


def test_language_config_tier1_and_tier2() -> None:
    """Verify Tier 1 has exactly 7 enabled languages, and Tier 2 has 5 languages."""
    lang_file = ROOT / "config" / "languages.yaml"
    assert lang_file.exists()
    data = yaml.safe_load(lang_file.read_text(encoding="utf-8")) or {}

    langs = {item["code"]: item for item in data.get("languages", [])}

    # Tier 1 languages must all be present, tier 1, and enabled
    for code in TIER1_LANGUAGES:
        assert code in langs, f"Missing Tier 1 language {code}"
        assert langs[code]["tier"] == 1, f"Expected tier 1 for {code}, got {langs[code]['tier']}"
        assert langs[code]["enabled"] is True, f"Tier 1 language {code} must be enabled"

    # Tier 2 languages
    for code in TIER2_LANGUAGES:
        assert code in langs, f"Missing Tier 2 language {code}"
        assert langs[code]["tier"] == 2, f"Expected tier 2 for {code}, got {langs[code]['tier']}"


def test_every_tier1_language_has_templates_glossary_and_ui_strings() -> None:
    """Every Tier-1 language must have alert templates, glossary terms, and UI strings."""
    tpl_file = ROOT / "seeds" / "i18n" / "alert-templates.yaml"
    assert tpl_file.exists()
    templates = yaml.safe_load(tpl_file.read_text(encoding="utf-8")) or {}

    for code in TIER1_LANGUAGES:
        # 1. Alert templates
        assert code in templates, f"alert-templates.yaml missing entries for {code}"
        for key in ["headline", "body", "meaning", "cancel", "advice_header"]:
            assert key in templates[code], f"Template for {code} missing required key '{key}'"

        # 2. Glossary
        gloss_file = ROOT / "seeds" / "i18n" / f"glossary.{code}.yaml"
        assert gloss_file.exists(), f"seeds/i18n/glossary.{code}.yaml missing for {code}"
        gloss_data = yaml.safe_load(gloss_file.read_text(encoding="utf-8")) or {}
        terms = gloss_data.get("terms", {})
        for term in ["rain", "heavy_rain", "heat_wave", "cold_wave", "thunderstorm", "temperature"]:
            assert term in terms, f"Glossary for {code} missing essential key '{term}'"

        # 3. UI strings
        ui_file = ROOT / "seeds" / "i18n" / f"ui.{code}.json"
        assert ui_file.exists(), f"seeds/i18n/ui.{code}.json missing for {code}"
        ui_data = json.loads(ui_file.read_text(encoding="utf-8"))
        for ui_key in ["app_name", "ask", "alerts", "settings", "language"]:
            assert ui_key in ui_data, f"UI strings for {code} missing key '{ui_key}'"


def test_language_detection_scripts_and_stopword_heuristics() -> None:
    """Verify script detection and Hindi vs Marathi stopword disambiguation."""
    # Bengali script
    assert detect_language("কাল কলকাতায় বৃষ্টি হবে কি?") == "bn"
    # Telugu script
    assert detect_language("రేపు హైదరాబాద్‌లో వర్షం పడుతుందా?") == "te"
    # Tamil script
    assert detect_language("நாளை சென்னையில் மழை பெய்யுமா?") == "ta"
    # Odia script
    assert detect_language("ଆସନ୍ତାକାଲି ଭୁବନେଶ୍ୱରରେ ବର୍ଷା ହେବ କି?") == "or"

    # Devanagari Hindi vs Marathi
    hindi_sample = "कल पुणे में बारिश होगी क्या?"
    marathi_sample = "उद्या पुण्यात पाऊस पडेल का?"
    assert detect_language(hindi_sample) == "hi"
    assert detect_language(marathi_sample) == "mr"

    # English / Hinglish
    assert detect_language("Will it rain tomorrow in Pune?") == "en"
    assert detect_language("kal Pune me barish hogi kya?") == "hi"


@pytest.mark.asyncio
async def test_conversation_agent_answers_all_tier1_languages() -> None:
    """Conversation agent returns cards and answer tokens for all Tier-1 languages."""
    agent = ConversationAgent()
    samples = [
        ("en", "Will it rain tomorrow in Pune?"),
        ("hi", "कल पुणे में बारिश होगी क्या?"),
        ("mr", "उद्या पुण्यात पाऊस पडेल का?"),
        ("bn", "কাল কলকাতায় বৃষ্টি হবে কি?"),
        ("te", "రేపు హైదరాబాద్‌లో వర్షం పడుతుందా?"),
        ("ta", "நாளை சென்னையில் மழை பெய்யுமா?"),
        ("or", "ଆସନ୍ତାକାଲି ଭୁବନେଶ୍ୱରରେ ବର୍ଷା ହେବ କି?"),
    ]
    for code, q in samples:
        req = ChatRequest(
            session_id=f"test_tier1_{code}",
            text=q,
            language=code,
            stream=True,
        )
        tokens = []
        card = None
        async for evt in agent.run_chat(req):
            if evt["event"] == "token":
                tokens.append(evt["data"]["text"])
            elif evt["event"] == "card":
                card = evt["data"]

        answer = "".join(tokens)
        assert len(answer) > 0, f"No answer tokens returned for language {code}"
        assert card is not None, f"No card emitted for language {code}"
        assert "headline" in card
        assert "key_values" in card
