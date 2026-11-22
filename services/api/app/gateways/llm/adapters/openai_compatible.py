"""OpenAI-compatible LLM Adapter (Ticket R2.2).

Supports tool calling, streaming via SSE, timeouts, retry with exponential backoff and jitter,
and token/latency instrumentation.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from typing import Any, AsyncGenerator

import httpx

from services.api.app.gateways.llm.adapters.base import LLMAdapter

logger = logging.getLogger(__name__)


class OpenAICompatibleLLMAdapter(LLMAdapter):
    def __init__(
        self,
        base_url: str = "https://api.groq.com/openai/v1",
        api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",
        provider_name: str = "groq",
        timeout: float = 30.0,
        max_retries: int = 2,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("GROQ_API_KEY", "")
        self.model = model
        self.provider_name = provider_name
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = client
        self.last_call_metrics: dict[str, Any] = {}

    def _get_headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError(f"API key not configured for provider {self.provider_name}")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        headers = self._get_headers()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        url = f"{self.base_url}/chat/completions"

        if stream:
            return self._stream_complete(url=url, payload=payload, headers=headers)
        return await self._non_stream_complete(url=url, payload=payload, headers=headers)

    async def _non_stream_complete(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        start_time = time.time()
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            client = self._client or httpx.AsyncClient(timeout=self.timeout)
            try:
                resp = await client.post(url, json=payload, headers=headers)
                # 429 and 5xx trigger retry with jitter or fallback
                if resp.status_code in (429, 502, 503, 504):
                    resp.raise_for_status()

                resp.raise_for_status()
                data = resp.json()
                latency_ms = int((time.time() - start_time) * 1000)

                choice = data["choices"][0]["message"]
                usage = data.get("usage", {})
                msg = dict(choice)
                msg["usage"] = usage
                msg["latency_ms"] = latency_ms
                msg["provider"] = self.provider_name
                msg["model"] = self.model

                self.last_call_metrics = {
                    "provider": self.provider_name,
                    "model": self.model,
                    "latency_ms": latency_ms,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
                return msg
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    delay = (0.2 * (2 ** attempt)) + random.uniform(0.01, 0.05)
                    logger.warning(
                        "llm_transient_error_retry",
                        extra={
                            "provider": self.provider_name,
                            "attempt": attempt + 1,
                            "delay": delay,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(delay)
                else:
                    raise
            finally:
                if not self._client:
                    await client.aclose()

        raise last_exc or RuntimeError(f"Failed to complete LLM request with {self.provider_name}")

    async def _stream_complete(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> AsyncGenerator[str, None]:
        start_time = time.time()
        client = self._client or httpx.AsyncClient(timeout=self.timeout)
        try:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    clean_line = line.strip()
                    if not clean_line or not clean_line.startswith("data:"):
                        continue
                    data_str = clean_line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue

            latency_ms = int((time.time() - start_time) * 1000)
            self.last_call_metrics = {
                "provider": self.provider_name,
                "model": self.model,
                "latency_ms": latency_ms,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        finally:
            if not self._client:
                await client.aclose()
