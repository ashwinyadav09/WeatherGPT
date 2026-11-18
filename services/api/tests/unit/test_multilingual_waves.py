from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from services.api.app.conversation.agent import ChatRequest, ConversationAgent

ROOT = Path(__file__).resolve().parents[4]


def test_language_config_waves_2_and_3() -> None:
    lang_file = ROOT / "config" / "languages.yaml"
    assert lang_file.exists()
    with lang_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    langs = {item["code"]: item for item in data.get("languages", [])}
    # Wave 2 languages
    for code in ["bn", "mr", "te", "ta"]:
        assert code in langs, f"Missing Wave 2 language {code}"
        assert langs[code]["tier"] == 2
        assert langs[code]["enabled"] is False, "Wave 2 languages must be disabled until signed off"

    # Wave 3 languages
    for code in ["gu", "kn", "ml", "pa", "or"]:
        assert code in langs, f"Missing Wave 3 language {code}"
        assert langs[code]["tier"] == 3
        assert langs[code]["enabled"] is False, "Wave 3 languages must be disabled"


def test_alert_templates_wave_2_backtranslations() -> None:
    tpl_file = ROOT / "seeds" / "i18n" / "alert-templates.yaml"
    assert tpl_file.exists()
    raw_content = tpl_file.read_text(encoding="utf-8")
    assert "Back-translation:" in raw_content, "Templates must contain back-translations"

    data = yaml.safe_load(raw_content)
    for code in ["mr", "bn", "te", "ta"]:
        assert code in data, f"Missing template entries for {code}"
        assert "headline" in data[code]
        assert "body" in data[code]
        assert "meaning" in data[code]
        assert "cancel" in data[code]
        assert "advice_header" in data[code]


def test_glossaries_wave_2_completeness() -> None:
    en_file = ROOT / "seeds" / "i18n" / "glossary.en.yaml"
    with en_file.open("r", encoding="utf-8") as f:
        en_terms = yaml.safe_load(f).get("terms", {})
        assert "rain" in en_terms

    for code in ["mr", "bn", "te", "ta"]:
        gloss_file = ROOT / "seeds" / "i18n" / f"glossary.{code}.yaml"
        assert gloss_file.exists(), f"Missing glossary for {code}"
        with gloss_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            terms = data.get("terms", {})
            for key in ["rain", "heavy_rain", "heat_wave", "cold_wave", "thunderstorm", "temperature"]:
                assert key in terms, f"Glossary for {code} missing essential key {key}"


@pytest.mark.asyncio
async def test_conversation_agent_wave_2_languages() -> None:
    agent = ConversationAgent()
    for code, q in [
        ("mr", "उद्या पुण्यात पाऊस पडेल का?"),
        ("bn", "কাল কলকাতায় বৃষ্টি হবে কি?"),
        ("te", "రేపు హైదరాబాద్‌లో వర్షం పడుతుందా?"),
        ("ta", "நாளை சென்னையில் மழை பெய்யுமா?"),
    ]:
        req = ChatRequest(
            session_id=f"test_wave2_{code}",
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
        assert len(answer) > 0
        assert card is not None
        assert "headline" in card
        assert "key_values" in card
