"""LLM Gateway with fallback chain and instrumentation (Ticket R2.2).

Orchestrates calls across LLM providers:
- Primary: Groq (llama-3.3-70b-versatile)
- Fallback: OpenRouter (meta-llama/llama-3.3-70b-instruct)
- Stub fallback for test/offline environments
- Tracks call metrics (latency_ms, prompt_tokens, completion_tokens, total_tokens, provider, model)
"""
from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

import httpx

from services.api.app.gateways.llm.adapters.base import LLMAdapter

logger = logging.getLogger(__name__)


class LLMGateway(LLMAdapter):
    def __init__(
        self,
        primary: LLMAdapter | None = None,
        fallback: LLMAdapter | None = None,
        stub: LLMAdapter | None = None,
    ) -> None:
        if primary:
            self.primary = primary
            self.fallback = fallback
            self.stub = stub
        else:
            from services.api.app.registry import registry

            # Build from registry
            reg_gateway = registry.get_llm_gateway()
            self.primary = reg_gateway.primary
            self.fallback = reg_gateway.fallback
            self.stub = reg_gateway.stub

        self.last_call_metrics: dict[str, Any] = {
            "provider": getattr(self.primary, "provider_name", "unknown"),
            "model": getattr(self.primary, "model", "unknown"),
            "latency_ms": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        providers_to_try = [p for p in (self.primary, self.fallback, self.stub) if p is not None]
        last_error: Exception | None = None

        for idx, provider in enumerate(providers_to_try):
            provider_name = getattr(provider, "provider_name", type(provider).__name__)
            try:
                res = await provider.complete(
                    messages=messages,
                    tools=tools,
                    stream=stream,
                    **kwargs,
                )

                if stream and isinstance(res, AsyncGenerator):
                    # res is an AsyncGenerator
                    async def _tracking_gen(gen: AsyncGenerator[str, None], p_inst: Any) -> AsyncGenerator[str, None]:
                        async for chunk in gen:
                            yield chunk
                        metrics = getattr(p_inst, "last_call_metrics", None)
                        if metrics:
                            self.last_call_metrics = dict(metrics)

                    return _tracking_gen(res, provider)

                # Non-streaming result dict
                metrics = getattr(provider, "last_call_metrics", None)
                if metrics:
                    self.last_call_metrics = dict(metrics)
                elif isinstance(res, dict):
                    usage = res.get("usage", {})
                    self.last_call_metrics = {
                        "provider": provider_name,
                        "model": getattr(provider, "model", "unknown"),
                        "latency_ms": res.get("latency_ms", 0),
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }
                return res

            except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError, ValueError, RuntimeError) as exc:
                last_error = exc
                next_p = (
                    getattr(providers_to_try[idx + 1], "provider_name", type(providers_to_try[idx + 1]).__name__)
                    if idx + 1 < len(providers_to_try)
                    else "none"
                )
                logger.warning(
                    "llm_primary_failed",
                    extra={
                        "provider": provider_name,
                        "error": str(exc),
                        "falling_back_to": next_p,
                    },
                )
                # If this provider was the last one, loop exits and raises
                continue

        raise last_error or RuntimeError("All LLM providers failed")
