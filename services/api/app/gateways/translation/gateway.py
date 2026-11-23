from __future__ import annotations

import logging
import re
from typing import Any

from services.api.app.gateways.speech.exceptions import ProviderNotConfigured
from services.api.app.gateways.translation.base import TranslationAdapter
from services.api.app.gateways.translation.cache import TranslationCache

logger = logging.getLogger(__name__)

# Native Indic digits translation table to standard ASCII digits 0-9
INDIC_DIGITS = (
    "०१२३४५६७८९"  # Devanagari (Hindi, Marathi)
    "০১২৩৪৫৬৭৮৯"  # Bengali
    "੦੧੨੩੪੫੬੭੮੯"  # Gurmukhi
    "૦૧૨૩૪૫૬૭୮૯"  # Gujarati
    "୦୧୨୩୪୫୬୭୮୯"  # Odia
    "௦௧௨௩௪௫௬௭௮௯"  # Tamil
    "౦౧౨౩౪౫౬౭౮౯"  # Telugu
    "೦೧೨೩೪೫೬೭೮೯"  # Kannada
    "൦൧൨൩൪൫൬൭൮൯"  # Malayalam
)
ASCII_DIGITS = "0123456789" * 9
DIGIT_TRANSLATION_TABLE = str.maketrans(INDIC_DIGITS, ASCII_DIGITS)


def normalise_indic_digits(text: str) -> str:
    """Normalise Indic native digits (Devanagari, Bengali, Telugu, Odia, etc.) to ASCII 0-9."""
    if not text:
        return ""
    return text.translate(DIGIT_TRANSLATION_TABLE)


# Regex pattern to match values with units and standalone numbers
VALUE_PATTERN = re.compile(
    r"(\b\d+(?:\.\d+)?\s*(?:mm|°C|℃|degC|%|km/h|kmh|celsius)\b|\b\d+(?:\.\d+)?\b)",
    re.IGNORECASE,
)


def protect_numbers_and_units(text: str) -> tuple[str, dict[str, str]]:
    """Replace numbers and units with placeholders before translation."""
    mapping: dict[str, str] = {}
    counter = 0

    def replacer(match: re.Match) -> str:
        nonlocal counter
        placeholder = f"__VAL_{counter}__"
        val = match.group(0)
        mapping[placeholder] = val
        counter += 1
        return placeholder

    protected = VALUE_PATTERN.sub(replacer, text)
    return protected, mapping


def restore_numbers_and_units(text: str, mapping: dict[str, str]) -> str:
    """Restore placeholders back to original numbers and units."""
    restored = text
    for placeholder, original in mapping.items():
        # Handle exact placeholder as well as minor spacing artifacts introduced by MT
        var_num = placeholder.strip("_")
        pattern = re.compile(r"__\s*" + re.escape(var_num) + r"\s*__")
        restored = pattern.sub(original, restored)
    return restored


class TranslationGateway:
    """Gateway orchestrating text translation with caching, protection, and failover.

    - Primary: Sarvam AI (mayura:v1)
    - Fallback: Groq LLM with domain glossary
    - Strict failover: Sarvam -> Groq LLM -> raise (never stub or silent fallback)
    - Cache key: sha256(text + src + tgt + glossary_version)
    - Protects numbers and units before translation, restores after.
    - Normalises native Indic digits to ASCII before returning.
    """

    def __init__(
        self,
        primary: TranslationAdapter | None = None,
        fallback: TranslationAdapter | None = None,
        cache: TranslationCache | None = None,
        glossary_version: str = "v1",
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.cache = cache or TranslationCache()
        self.glossary_version = glossary_version

    async def translate(
        self,
        text: str,
        src: str = "en",
        tgt: str = "hi",
        **kwargs: Any,
    ) -> str:
        if not text or not text.strip():
            return text

        src_clean = src.strip().lower().split("-")[0]
        tgt_clean = tgt.strip().lower().split("-")[0]

        if src_clean == tgt_clean:
            return text

        # 1. Check cache first
        cached = self.cache.get(text, src_clean, tgt_clean, self.glossary_version)
        if cached is not None:
            return cached

        # 2. Protect numbers and units with placeholders
        protected_text, mapping = protect_numbers_and_units(text)

        translated_protected: str | None = None
        active_adapter: TranslationAdapter | None = None

        # 3. Try primary translation adapter (Sarvam), then fallback (Groq LLM), then raise
        if self.primary:
            try:
                translated_protected = await self.primary.translate(
                    protected_text, src=src_clean, tgt=tgt_clean, **kwargs
                )
                active_adapter = self.primary
            except (ProviderNotConfigured, Exception) as exc:
                logger.warning(
                    "translation_primary_failed",
                    extra={
                        "provider": getattr(self.primary, "source_id", "primary"),
                        "error": str(exc),
                        "falling_back": bool(self.fallback),
                    },
                )
                if self.fallback:
                    translated_protected = await self.fallback.translate(
                        protected_text, src=src_clean, tgt=tgt_clean, **kwargs
                    )
                    active_adapter = self.fallback
                else:
                    raise
        elif self.fallback:
            translated_protected = await self.fallback.translate(
                protected_text, src=src_clean, tgt=tgt_clean, **kwargs
            )
            active_adapter = self.fallback
        else:
            raise ProviderNotConfigured("No translation provider configured.")

        if not translated_protected:
            raise RuntimeError("Translation provider returned empty text.")

        # 4. Restore numbers and units
        restored = restore_numbers_and_units(translated_protected, mapping)

        # 5. Normalise any native Indic digits to ASCII
        final_text = normalise_indic_digits(restored)

        # 6. Store in cache
        adapter_id = getattr(active_adapter, "source_id", "unknown")
        self.cache.set(text, src_clean, tgt_clean, final_text, self.glossary_version, adapter_id=adapter_id)
        return final_text
