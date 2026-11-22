from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[5]
DEFAULT_CACHE_DIR = ROOT / ".cache" / "translations"


class TranslationCache:
    """Disk-backed and in-memory translation cache.

    Cache key is sha256(text + src + tgt + glossary_version) per REMEDIATION_PLAN.md R1.2.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, str] = {}

    def compute_key(self, text: str, src: str, tgt: str, glossary_version: str = "v1") -> str:
        payload = f"{text}:{src}:{tgt}:{glossary_version}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def get(self, text: str, src: str, tgt: str, glossary_version: str = "v1") -> str | None:
        key = self.compute_key(text, src, tgt, glossary_version)
        if key in self._memory_cache:
            return self._memory_cache[key]

        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                val = data.get("translation")
                if isinstance(val, str):
                    self._memory_cache[key] = val
                    return val
            except Exception as e:
                logger.warning("translation_cache_read_error", extra={"key": key, "error": str(e)})

        return None

    def set(self, text: str, src: str, tgt: str, translation: str, glossary_version: str = "v1") -> None:
        key = self.compute_key(text, src, tgt, glossary_version)
        self._memory_cache[key] = translation

        cache_file = self.cache_dir / f"{key}.json"
        try:
            cache_file.write_text(
                json.dumps(
                    {
                        "key": key,
                        "text": text,
                        "src": src,
                        "tgt": tgt,
                        "glossary_version": glossary_version,
                        "translation": translation,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("translation_cache_write_error", extra={"key": key, "error": str(e)})
