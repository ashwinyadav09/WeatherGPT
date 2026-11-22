from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from services.api.app.config import settings
from services.api.app.gateways.speech.exceptions import ProviderNotConfigured
from services.api.app.gateways.translation.base import TranslationAdapter

logger = logging.getLogger(__name__)

SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"

LANGUAGE_CODE_MAP = {
    "en": "en-IN",
    "hi": "hi-IN",
    "bn": "bn-IN",
    "mr": "mr-IN",
    "te": "te-IN",
    "ta": "ta-IN",
    "or": "od-IN",
    "od": "od-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
}


class SarvamTranslationAdapter(TranslationAdapter):
    """Sarvam AI translation adapter using model 'mayura:v1'."""

    def __init__(
        self,
        api_key: str | None = None,
        client: httpx.AsyncClient | None = None,
        base_url: str = SARVAM_TRANSLATE_URL,
    ) -> None:
        self.api_key = api_key if api_key is not None else (settings.sarvam_api_key or os.getenv("SARVAM_API_KEY", ""))
        self.client = client
        self.base_url = base_url

    @property
    def source_id(self) -> str:
        return "sarvam.translation"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _normalize_lang(self, code: str) -> str:
        cleaned = code.strip().lower()
        if "-" in cleaned:
            cleaned = cleaned.split("-")[0]
        return LANGUAGE_CODE_MAP.get(cleaned, f"{cleaned}-IN")

    async def translate(
        self,
        text: str,
        src: str = "en",
        tgt: str = "hi",
        **kwargs: Any,
    ) -> str:
        if not self.is_configured():
            raise ProviderNotConfigured("Sarvam API key is not configured for translation.")

        src_code = self._normalize_lang(src)
        tgt_code = self._normalize_lang(tgt)

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }
        body = {
            "input": text,
            "source_language_code": src_code,
            "target_language_code": tgt_code,
            "model": "mayura:v1",
            "mode": kwargs.get("mode", "formal"),
        }

        if self.client:
            resp = await self.client.post(self.base_url, headers=headers, json=body, timeout=15.0)
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.base_url, headers=headers, json=body, timeout=15.0)

        if resp.status_code != 200:
            logger.warning(
                "sarvam_translate_http_error",
                extra={"status_code": resp.status_code, "body": resp.text[:200]},
            )
            raise RuntimeError(f"Sarvam translation failed with HTTP {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        translated = data.get("translated_text", "")
        if not translated:
            raise RuntimeError("Sarvam returned empty translation response.")
        return translated
