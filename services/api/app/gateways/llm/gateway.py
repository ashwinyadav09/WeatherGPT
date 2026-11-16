from __future__ import annotations

import os
from typing import Any, AsyncGenerator

from services.api.app.config import settings
from services.api.app.gateways.llm.adapters.base import LLMAdapter
from services.api.app.gateways.llm.adapters.openai_compatible import OpenAICompatibleLLMAdapter
from services.api.app.gateways.llm.adapters.stub import StubLLMAdapter


class LLMGateway:
    def __init__(self, adapter: LLMAdapter | None = None) -> None:
        if adapter:
            self.adapter = adapter
        else:
            # Check if groq or openrouter key exists in env
            groq_key = os.getenv("GROQ_API_KEY")
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if groq_key:
                self.adapter = OpenAICompatibleLLMAdapter(
                    base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
                    api_key=groq_key,
                    model=settings.models.main_model if settings.models else "llama-3.3-70b-versatile",
                )
            elif openrouter_key:
                self.adapter = OpenAICompatibleLLMAdapter(
                    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                    api_key=openrouter_key,
                    model=settings.models.main_model if settings.models else "meta-llama/llama-3.3-70b-instruct",
                )
            else:
                self.adapter = StubLLMAdapter()

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        return await self.adapter.complete(messages=messages, tools=tools, stream=stream, **kwargs)
