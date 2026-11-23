from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from services.api.app.gateways.speech.exceptions import ProviderNotConfigured
from services.api.app.gateways.translation.base import TranslationAdapter

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[5]
SEEDS_I18N = ROOT / "seeds" / "i18n"


class LLMTranslationAdapter(TranslationAdapter):
    """Fallback translation adapter using Groq LLM with domain glossary in the prompt."""

    def __init__(self, llm: Any | None = None) -> None:
        if llm:
            self.llm = llm
        else:
            from services.api.app.gateways.llm.gateway import LLMGateway
            from services.api.app.registry import registry

            reg_gateway = registry.get_llm_gateway()
            # Per R8.3: Remove stub from the translation chain (Groq LLM only, no stub fallback)
            self.llm = LLMGateway(primary=reg_gateway.primary, fallback=reg_gateway.fallback, stub=None)
        self._glossaries: dict[str, dict[str, Any]] = {}
        self._load_glossaries()

    @property
    def source_id(self) -> str:
        return "groq.translation"

    def is_configured(self) -> bool:
        if hasattr(self.llm, "is_configured"):
            return self.llm.is_configured()
        if hasattr(self.llm, "primary") and self.llm.primary:
            return bool(getattr(self.llm.primary, "api_key", None))
        if hasattr(self.llm, "api_key"):
            return bool(self.llm.api_key and self.llm.api_key.strip())
        return False

    def _load_glossaries(self) -> None:
        if not SEEDS_I18N.exists():
            return
        for p in SEEDS_I18N.glob("glossary.*.yaml"):
            lang = p.stem.split(".")[-1]
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                self._glossaries[lang] = data.get("terms", {})
            except Exception as e:
                logger.warning("failed_loading_glossary", extra={"path": str(p), "error": str(e)})

    async def translate(
        self,
        text: str,
        src: str = "en",
        tgt: str = "hi",
        **kwargs: Any,
    ) -> str:
        if not self.is_configured():
            raise ProviderNotConfigured("Groq LLM is not configured for translation.")

        glossary_terms = self._glossaries.get(tgt, {})
        glossary_sample = "\n".join(f"- {k}: {v}" for k, v in list(glossary_terms.items())[:20])

        system_prompt = (
            f"You are a professional weather translator translating official meteorological forecasts "
            f"from '{src}' to '{tgt}'.\n"
            f"Rules:\n"
            f"1. Translate accurately and naturally into standard {tgt}.\n"
            f"2. CRITICAL: Preserve all placeholders exactly as they appear (e.g. __VAL_0__, __NUM_1__). "
            f"Do not alter, translate, or remove them.\n"
            f"3. Use standard meteorological terms. Relevant domain glossary:\n{glossary_sample}\n"
            f"4. Output ONLY the translated text without explanations, prefixes, or quotes."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ]

        res = await self.llm.complete(messages=messages, temperature=0.0, max_tokens=600)
        if isinstance(res, dict):
            raw_text = res.get("content", "")
        else:
            raw_text = str(res)

        cleaned = (raw_text or "").strip().strip('"').strip("'")
        if "according to open-meteo" in cleaned.lower():
            raise RuntimeError("LLM returned stub sentence instead of real translation.")
        if not cleaned:
            raise RuntimeError("LLM returned empty translation.")
        return cleaned
