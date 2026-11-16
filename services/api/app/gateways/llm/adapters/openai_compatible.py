from __future__ import annotations

import os
from typing import Any, AsyncGenerator

import httpx

from services.api.app.gateways.llm.adapters.base import LLMAdapter


class OpenAICompatibleLLMAdapter(LLMAdapter):
    def __init__(
        self,
        base_url: str = "https://api.groq.com/openai/v1",
        api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.model = model

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        if not self.api_key:
            raise ValueError("API key not configured for OpenAI-compatible provider")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]
            return choice
