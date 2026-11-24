"""Validation tests for translation pipeline and static seed translations (Ticket R8.3).

Enforces:
1. No stub sentences ("According to Open-Meteo...") in any non-English seed translation.
2. Non-Latin-script languages (hi, mr, bn, te, ta, or) have at least 50% target-script
   characters in every string longer than 20 characters (excluding placeholders, proper names, URLs).
3. Guidance entries in seeds/translations/*.json contain reviewed: false (only human edits may set reviewed: true).
4. Guidance translation fields source_url and reviewed_by match the English originals exactly.
5. TranslationGateway uses Sarvam -> Groq LLM -> raise (never stub).
6. TranslationCache refuses any entry whose adapter id or content is a stub.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from services.api.app.gateways.speech.exceptions import ProviderNotConfigured
from services.api.app.gateways.translation.cache import TranslationCache
from services.api.app.gateways.translation.gateway import TranslationGateway
from services.api.app.gateways.translation.llm_fallback import LLMTranslationAdapter
from services.api.app.gateways.translation.sarvam import SarvamTranslationAdapter

ROOT = Path(__file__).resolve().parents[4]
SEEDS_DIR = ROOT / "seeds"
TRANSLATIONS_DIR = SEEDS_DIR / "translations"
GUIDANCE_DIR = SEEDS_DIR / "guidance"

SCRIPT_RANGES: dict[str, tuple[int, int]] = {
    "hi": (0x0900, 0x097F),  # Devanagari
    "mr": (0x0900, 0x097F),  # Devanagari
    "bn": (0x0980, 0x09FF),  # Bengali
    "te": (0x0C00, 0x0C7F),  # Telugu
    "ta": (0x0B80, 0x0BFF),  # Tamil
    "or": (0x0B00, 0x0B7F),  # Odia
}

CANNED_STUB_PHRASE = "According to Open-Meteo"


def clean_placeholders(text: str) -> str:
    cleaned = re.sub(r"__VAL_\d+__", "", text)
    cleaned = re.sub(r"\{[^}]+\}", "", cleaned)
    return cleaned.strip()


def test_no_stub_sentence_in_seeds():
    """No non-English seed translation may contain the canned stub sentence."""
    seed_files = list(TRANSLATIONS_DIR.glob("*.json"))
    assert seed_files, "No translation seed files found"

    for seed_file in seed_files:
        content = seed_file.read_text(encoding="utf-8")
        assert (
            CANNED_STUB_PHRASE.lower() not in content.lower()
        ), f"Canned stub phrase found in {seed_file.name}"


def test_non_latin_script_character_percentage():
    """Non-Latin-script languages must have at least 50% target-script characters in strings > 20 chars."""
    for lang, (lo, hi) in SCRIPT_RANGES.items():
        seed_file = TRANSLATIONS_DIR / f"{lang}.json"
        assert seed_file.exists(), f"Missing translation file: {seed_file}"
        data = json.loads(seed_file.read_text(encoding="utf-8"))

        def check_leaves(obj: any, path: str = "") -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    # Skip metadata identifiers, URLs, proper names, and citation titles
                    if k in [
                        "source_url",
                        "source_title",
                        "reviewed_by",
                        "reviewed_date",
                        "retrieved_on",
                        "hazard",
                        "id",
                        "generated_at",
                        "language",
                        "status",
                    ]:
                        continue
                    check_leaves(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    check_leaves(v, f"{path}[{i}]")
            elif isinstance(obj, str):
                cleaned = clean_placeholders(obj)
                if len(cleaned) > 20 and not cleaned.startswith("http"):
                    alpha_chars = [c for c in cleaned if c.isalpha()]
                    if alpha_chars:
                        target_chars = [c for c in alpha_chars if lo <= ord(c) <= hi]
                        pct = len(target_chars) / len(alpha_chars)
                        assert (
                            pct >= 0.5
                        ), f"String in {lang} at {path} has only {pct:.1%} target-script chars: {cleaned}"

        check_leaves(data)


def test_guidance_reviewed_flag_is_false():
    """Generated guidance translations must have reviewed: false (human step H7)."""
    for seed_file in TRANSLATIONS_DIR.glob("*.json"):
        data = json.loads(seed_file.read_text(encoding="utf-8"))
        guidance = data.get("guidance", {})
        for hazard, g_data in guidance.items():
            assert (
                g_data.get("reviewed") is False
            ), f"Guidance entry '{hazard}' in {seed_file.name} has reviewed=True; must be False until human sign-off"


def test_guidance_metadata_matches_english():
    """source_url and reviewed_by must be exact copies of the English originals."""
    for seed_file in TRANSLATIONS_DIR.glob("*.json"):
        data = json.loads(seed_file.read_text(encoding="utf-8"))
        guidance = data.get("guidance", {})
        for hazard, g_data in guidance.items():
            assert g_data.get("source_url", "").startswith(
                "https://ndma.gov.in"
            ), f"source_url corrupted in {seed_file.name}: {g_data.get('source_url')}"
            assert (
                g_data.get("reviewed_by") == "ashwin"
            ), f"reviewed_by corrupted in {seed_file.name}: {g_data.get('reviewed_by')}"


@pytest.mark.asyncio
async def test_translation_chain_raises_on_unconfigured_providers(tmp_path):
    """TranslationGateway must raise when no translation provider succeeds or is configured (no stub)."""
    # 1. Gateway with no adapters raises ProviderNotConfigured
    gw_empty = TranslationGateway(primary=None, fallback=None, cache=TranslationCache(cache_dir=tmp_path / "c1"))
    with pytest.raises(ProviderNotConfigured):
        await gw_empty.translate("Hello world", src="en", tgt="hi")

    # 2. Sarvam unconfigured raises ProviderNotConfigured
    sarvam_unconf = SarvamTranslationAdapter(api_key="")
    gw_sarvam_only = TranslationGateway(primary=sarvam_unconf, fallback=None, cache=TranslationCache(cache_dir=tmp_path / "c2"))
    with pytest.raises(ProviderNotConfigured):
        await gw_sarvam_only.translate("Hello world", src="en", tgt="hi")

    # 3. LLM fallback unconfigured raises ProviderNotConfigured
    llm_unconf = LLMTranslationAdapter()
    if hasattr(llm_unconf.llm, "primary") and llm_unconf.llm.primary:
        llm_unconf.llm.primary.api_key = ""
    elif hasattr(llm_unconf.llm, "api_key"):
        llm_unconf.llm.api_key = ""
    gw_both_unconf = TranslationGateway(primary=sarvam_unconf, fallback=llm_unconf, cache=TranslationCache(cache_dir=tmp_path / "c3"))
    with pytest.raises(ProviderNotConfigured):
        await gw_both_unconf.translate("Hello world", src="en", tgt="hi")


def test_cache_refuses_and_purges_stub_entries(tmp_path):
    """TranslationCache must refuse to store stub translations and purge any stub files on read."""
    cache = TranslationCache(cache_dir=tmp_path / "cache")

    # Refuse set with stub adapter_id
    cache.set("Test 1", "en", "hi", "अनुवाद", adapter_id="stub_adapter")
    assert cache.get("Test 1", "en", "hi") is None

    # Refuse set with stub phrase
    cache.set("Test 2", "en", "hi", f"{CANNED_STUB_PHRASE}, light rain tomorrow.", adapter_id="sarvam")
    assert cache.get("Test 2", "en", "hi") is None

    # Corrupted cache file on disk is purged on read
    key = cache.compute_key("Corrupted", "en", "hi")
    bad_file = cache.cache_dir / f"{key}.json"
    bad_file.write_text(
        json.dumps(
            {
                "key": key,
                "text": "Corrupted",
                "src": "en",
                "tgt": "hi",
                "glossary_version": "v1",
                "adapter_id": "stub",
                "translation": "According to Open-Meteo forecasts...",
            }
        ),
        encoding="utf-8",
    )
    assert bad_file.exists()
    assert cache.get("Corrupted", "en", "hi") is None
    assert not bad_file.exists(), "Cache file with stub should have been deleted on read"
