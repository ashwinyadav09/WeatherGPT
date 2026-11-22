from __future__ import annotations

from typing import Any, AsyncGenerator

from services.api.app.gateways.llm.adapters.base import LLMAdapter


class LLMGateway:
    def __init__(self, adapter: LLMAdapter | None = None) -> None:
        if adapter:
            self.adapter = adapter
        else:
            from services.api.app.registry import get_llm_adapter

            self.adapter = get_llm_adapter()

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        return await self.adapter.complete(messages=messages, tools=tools, stream=stream, **kwargs)
