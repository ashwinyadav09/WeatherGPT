from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "eval" / "llm_cache"

logger = logging.getLogger("llm_cache")

# Minimum interval between API calls in seconds (integers only for strict guard compliance)
PROVIDER_MIN_INTERVAL_SECONDS: dict[str, int] = {
    "groq": 2,        # Groq free tier rate limit
    "openrouter": 1,  # OpenRouter rate limit
    "sarvam": 1,      # Sarvam credits preservation
    "default": 1,
}


def compute_cache_key(
    provider: str,
    model: str,
    messages: Any,
    parameters: dict[str, Any] | None = None,
) -> str:
    """Compute deterministic SHA-256 hash for LLM/Sarvam call arguments."""
    norm_provider = str(provider).strip().lower()
    norm_model = str(model).strip().lower()

    if isinstance(messages, list):
        norm_messages: list[dict[str, str]] = []
        for m in messages:
            if isinstance(m, dict):
                norm_messages.append({
                    "role": str(m.get("role", "")).strip(),
                    "content": str(m.get("content", "")).strip(),
                })
            else:
                norm_messages.append({"role": "user", "content": str(m).strip()})
    elif isinstance(messages, dict):
        norm_messages = [{"role": str(messages.get("role", "")), "content": str(messages.get("content", ""))}]
    else:
        norm_messages = [{"role": "user", "content": str(messages).strip()}]

    norm_params: dict[str, Any] = {}
    if parameters:
        for k, v in sorted(parameters.items()):
            if k in ("stream", "client", "timeout"):
                continue
            norm_params[k] = v

    canonical_obj = {
        "provider": norm_provider,
        "model": norm_model,
        "messages": norm_messages,
        "parameters": norm_params,
    }
    serialized = json.dumps(canonical_obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_cached_entry(cache_key: str, cache_dir: Path | None = None) -> dict[str, Any] | None:
    """Retrieve cached call entry if present on disk. Marks replayed=True."""
    target_dir = cache_dir or CACHE_DIR
    target_file = target_dir / f"{cache_key}.json"
    if not target_file.exists():
        return None

    try:
        data = json.loads(target_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            # Replays are allowed for reproducibility and record replayed: true
            data["replayed"] = True
            return data
    except Exception as exc:
        logger.warning("Could not read cache file %s: %s", target_file, exc)
    return None


def put_cached_entry(
    cache_key: str,
    provider: str,
    model: str,
    messages: Any,
    parameters: dict[str, Any] | None,
    response: Any,
    latency_ms: int,
    token_counts: dict[str, int] | None = None,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Store raw real response to cache with provenance: recorded_real_http."""
    target_dir = cache_dir or CACHE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{cache_key}.json"

    counts = token_counts or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    timestamp_str = dt.datetime.now(dt.timezone.utc).isoformat()

    entry: dict[str, Any] = {
        "cache_key": cache_key,
        "provider": provider,
        "model": model,
        "messages": messages,
        "parameters": parameters or {},
        "response": response,
        "latency_ms": int(latency_ms),
        "token_counts": counts,
        "timestamp": timestamp_str,
        "provenance": "recorded_real_http",
        "replayed": False,
    }

    target_file.write_text(json.dumps(entry, indent=2, ensure_ascii=False), encoding="utf-8")
    return entry


class ProviderThrottler:
    """Enforce rate limits across API calls and record throttle time."""

    def __init__(self) -> None:
        self.last_call_time: dict[str, int] = {}
        self.total_throttle_ms: int = 0
        self.throttled_calls: int = 0

    async def throttle(self, provider: str) -> int:
        """Throttle if needed to respect provider rate limits. Returns wait ms."""
        norm_prov = provider.strip().lower()
        min_interval = PROVIDER_MIN_INTERVAL_SECONDS.get(norm_prov, PROVIDER_MIN_INTERVAL_SECONDS["default"])

        now_sec = int(time.time())
        last_sec = self.last_call_time.get(norm_prov, 0)
        elapsed = now_sec - last_sec
        wait_ms = 0

        if elapsed < min_interval:
            wait_sec = min_interval - elapsed
            wait_ms = wait_sec * 1000
            self.total_throttle_ms += wait_ms
            self.throttled_calls += 1
            await asyncio.sleep(wait_sec)

        self.last_call_time[norm_prov] = int(time.time())
        return wait_ms
