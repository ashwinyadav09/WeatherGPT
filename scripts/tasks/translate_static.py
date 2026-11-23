"""Pre-translate static strings into seeds/translations/<lang>.json (Ticket R1.2, R8.3).

Extracts and translates:
- UI strings from seeds/i18n/ui.en.json
- Alert answer templates from seeds/i18n/alert-templates.yaml
- Domain glossary from seeds/i18n/glossary.en.yaml
- Guidance cards from seeds/guidance/*.yaml

Writes to seeds/translations/<lang>.json for Tier-1 languages:
["hi", "bn", "mr", "te", "ta", "or"].
Files are marked "status": "pending_human_review".
Guidance cards are generated with reviewed: false and copies of English metadata.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.api.app.gateways.translation.gateway import TranslationGateway
from services.api.app.registry import get_translation_provider

logger = logging.getLogger(__name__)

SEEDS_DIR = ROOT / "seeds"
I18N_DIR = SEEDS_DIR / "i18n"
GUIDANCE_DIR = SEEDS_DIR / "guidance"
OUTPUT_DIR = SEEDS_DIR / "translations"

TIER1_LANGUAGES = ["hi", "bn", "mr", "te", "ta", "or"]


def load_english_sources() -> dict[str, Any]:
    sources: dict[str, Any] = {"ui": {}, "templates": {}, "glossary": {}, "guidance": {}}

    # 1. UI strings
    ui_en = I18N_DIR / "ui.en.json"
    if ui_en.exists():
        sources["ui"] = json.loads(ui_en.read_text(encoding="utf-8"))

    # 2. Alert templates
    tpl_file = I18N_DIR / "alert-templates.yaml"
    if tpl_file.exists():
        data = yaml.safe_load(tpl_file.read_text(encoding="utf-8")) or {}
        sources["templates"] = data.get("en", {})

    # 3. Glossary
    glossary_en = I18N_DIR / "glossary.en.yaml"
    if glossary_en.exists():
        data = yaml.safe_load(glossary_en.read_text(encoding="utf-8")) or {}
        sources["glossary"] = data

    # 4. Guidance cards
    if GUIDANCE_DIR.exists():
        for g_file in GUIDANCE_DIR.glob("*.yaml"):
            try:
                g_data = yaml.safe_load(g_file.read_text(encoding="utf-8")) or {}
                sources["guidance"][g_file.stem] = g_data
            except Exception as e:
                logger.warning("failed_reading_guidance", extra={"file": str(g_file), "error": str(e)})

    return sources


def load_existing_seed_translations(lang: str) -> dict[str, Any]:
    """Load existing human-vetted or draft translations from seeds/i18n/ and seeds/guidance/."""
    existing: dict[str, Any] = {"ui": {}, "templates": {}, "glossary": {}, "guidance": {}}

    ui_file = I18N_DIR / f"ui.{lang}.json"
    if ui_file.exists():
        try:
            existing["ui"] = json.loads(ui_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    glossary_file = I18N_DIR / f"glossary.{lang}.yaml"
    if glossary_file.exists():
        try:
            data = yaml.safe_load(glossary_file.read_text(encoding="utf-8")) or {}
            existing["glossary"] = data
        except Exception:
            pass

    tpl_file = I18N_DIR / "alert-templates.yaml"
    if tpl_file.exists():
        try:
            data = yaml.safe_load(tpl_file.read_text(encoding="utf-8")) or {}
            if lang in data:
                existing["templates"] = data[lang]
        except Exception:
            pass

    if GUIDANCE_DIR.exists():
        for g_file in GUIDANCE_DIR.glob("*.yaml"):
            try:
                g_data = yaml.safe_load(g_file.read_text(encoding="utf-8")) or {}
                entries = g_data.get("entries", {})
                if lang in entries:
                    existing["guidance"][g_file.stem] = {
                        "hazard": g_data.get("hazard", g_file.stem),
                        "reviewed_by": g_data.get("reviewed_by", "ashwin"),
                        "reviewed_date": g_data.get("reviewed_date", "2026-11-17"),
                        "source_title": g_data.get("source_title", ""),
                        "source_url": g_data.get("source_url", ""),
                        "retrieved_on": g_data.get("retrieved_on", "2026-11-17"),
                        "reviewed": False,  # Scripts must write reviewed: false per R8.3
                        "entries": {
                            lang: entries.get(lang, {}),
                        },
                    }
            except Exception as e:
                logger.warning("failed_reading_guidance_entries", extra={"file": str(g_file), "error": str(e)})

    return existing


async def translate_dict_leaves(
    data: Any,
    translator: TranslationGateway,
    target_lang: str,
    existing: Any = None,
) -> Any:
    if isinstance(data, dict):
        res = {}
        for k, v in data.items():
            ex_val = existing.get(k) if isinstance(existing, dict) else None
            res[k] = await translate_dict_leaves(v, translator, target_lang, ex_val)
        return res
    elif isinstance(data, list):
        res_list = []
        for i, item in enumerate(data):
            ex_val = existing[i] if isinstance(existing, list) and i < len(existing) else None
            res_list.append(await translate_dict_leaves(item, translator, target_lang, ex_val))
        return res_list
    elif isinstance(data, str):
        if existing and isinstance(existing, str) and existing.strip():
            return existing
        return await translator.translate(data, src="en", tgt=target_lang)
    return data


async def pre_translate_language(
    lang: str,
    sources: dict[str, Any],
    translator: TranslationGateway,
) -> dict[str, Any]:
    existing = load_existing_seed_translations(lang)

    translated_ui = await translate_dict_leaves(sources["ui"], translator, lang, existing["ui"])
    translated_templates = await translate_dict_leaves(sources["templates"], translator, lang, existing["templates"])
    translated_glossary = await translate_dict_leaves(sources["glossary"], translator, lang, existing["glossary"])

    # Guidance translations with copies of English metadata and reviewed: false
    translated_guidance: dict[str, Any] = {}
    for g_id, g_data in sources["guidance"].items():
        ex_g = existing.get("guidance", {}).get(g_id)
        if ex_g:
            translated_guidance[g_id] = ex_g
        else:
            en_entry = g_data.get("entries", {}).get("en", {})
            tgt_title = await translator.translate(en_entry.get("title", ""), src="en", tgt=lang) if en_entry.get("title") else ""
            tgt_items = []
            for itm in en_entry.get("items", []):
                tgt_items.append(await translator.translate(itm, src="en", tgt=lang))
            translated_guidance[g_id] = {
                "hazard": g_data.get("hazard", g_id),
                "reviewed_by": g_data.get("reviewed_by", "ashwin"),
                "reviewed_date": g_data.get("reviewed_date", "2026-11-17"),
                "source_title": g_data.get("source_title", ""),
                "source_url": g_data.get("source_url", ""),
                "retrieved_on": g_data.get("retrieved_on", "2026-11-17"),
                "reviewed": False,
                "entries": {
                    lang: {
                        "id": f"ndma_guidance_{g_id}_{lang}",
                        "title": tgt_title,
                        "items": tgt_items,
                    },
                },
            }

    return {
        "language": lang,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "pending_human_review",
        "human_review_required": True,
        "ui": translated_ui,
        "templates": translated_templates,
        "glossary": translated_glossary,
        "guidance": translated_guidance,
    }


async def main_async(languages: list[str]) -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_english_sources()
    translator = get_translation_provider()

    print(f"Pre-translating static strings for languages: {', '.join(languages)}...")
    for lang in languages:
        result = await pre_translate_language(lang, sources, translator)
        out_file = OUTPUT_DIR / f"{lang}.json"
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✓ Wrote {out_file.relative_to(ROOT)} ({len(json.dumps(result))} bytes)")

    print("Static translation complete. All files saved to seeds/translations/.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-translate static strings into seeds/translations/<lang>.json")
    parser.add_argument(
        "--lang",
        nargs="+",
        default=TIER1_LANGUAGES,
        help="Target languages to pre-translate (defaults to all Tier-1)",
    )
    args = parser.parse_args()
    return asyncio.run(main_async(args.lang))


if __name__ == "__main__":
    raise SystemExit(main())
