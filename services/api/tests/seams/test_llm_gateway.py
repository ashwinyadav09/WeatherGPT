"""Seam tests for LLM Gateway upgrade (Ticket R2.2).

Requirements:
- Tool calling in OpenAICompatibleLLMAdapter.
- Streaming in OpenAICompatibleLLMAdapter (SSE parsing yielding tokens).
- Fallback chain: Groq primary, OpenRouter fallback on 429/error/timeout.
- Timeout and retry with jitter on transient failures.
- Record tokens (prompt, completion, total) and latency per call.
- All tests use httpx.MockTransport (no real API calls).
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
import pytest

from services.api.app.gateways.llm.adapters.openai_compatible import OpenAICompatibleLLMAdapter
from services.api.app.gateways.llm.gateway import LLMGateway


@pytest.mark.asyncio
async def test_tool_calling_round_trip() -> None:
    """Tool calling sends tools payload, parses tool_calls in response, records usage and latency."""
    request_payload: dict[str, Any] = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_payload
        request_payload = json.loads(request.content.decode("utf-8"))
        data = {
            "id": "chatcmpl_mock_1",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_geo_1",
                                "type": "function",
                                "function": {
                                    "name": "geocode",
                                    "arguments": '{"text": "Pune"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {
                "prompt_tokens": 85,
                "completion_tokens": 24,
                "total_tokens": 109,
            },
        }
        return httpx.Response(200, json=data)

    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    adapter = OpenAICompatibleLLMAdapter(
        base_url="https://api.groq.com/openai/v1",
        api_key="mock-groq-key",
        model="llama-3.3-70b-versatile",
        client=client,
    )
    gateway = LLMGateway(primary=adapter)

    tools = [
        {
            "type": "function",
            "function": {
                "name": "geocode",
                "description": "Geocode place",
                "parameters": {"type": "object", "properties": {"text": {"type": "string"}}},
            },
        }
    ]
    messages = [{"role": "user", "content": "What is the weather in Pune?"}]

    res = await gateway.complete(messages=messages, tools=tools)

    # 1. Tools were passed in request
    assert "tools" in request_payload
    assert request_payload["tools"][0]["function"]["name"] == "geocode"

    # 2. Response contains tool_calls
    assert res.get("tool_calls") is not None
    assert len(res["tool_calls"]) == 1
    call = res["tool_calls"][0]
    assert call["function"]["name"] == "geocode"
    assert json.loads(call["function"]["arguments"]) == {"text": "Pune"}

    # 3. Usage and latency recorded
    metrics = gateway.last_call_metrics
    assert metrics is not None
    assert metrics["prompt_tokens"] == 85
    assert metrics["completion_tokens"] == 24
    assert metrics["total_tokens"] == 109
    assert metrics["latency_ms"] >= 0
    assert metrics["provider"] == "groq"
    assert metrics["model"] == "llama-3.3-70b-versatile"


@pytest.mark.asyncio
async def test_streaming_sse_yields_tokens() -> None:
    """Streaming returns an AsyncGenerator yielding tokens parsed from SSE chunks."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        sse_body = (
            'data: {"choices": [{"delta": {"content": "Tomorrow "}}]}\n\n'
            'data: {"choices": [{"delta": {"content": "in Pune "}}]}\n\n'
            'data: {"choices": [{"delta": {"content": "will be clear."}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            content=sse_body.encode("utf-8"),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    adapter = OpenAICompatibleLLMAdapter(
        base_url="https://api.groq.com/openai/v1",
        api_key="mock-groq-key",
        model="llama-3.3-70b-versatile",
        client=client,
    )
    gateway = LLMGateway(primary=adapter)

    stream_gen = await gateway.complete(
        messages=[{"role": "user", "content": "Weather tomorrow?"}],
        stream=True,
    )

    tokens = []
    async for tok in stream_gen:
        tokens.append(tok)

    assert tokens == ["Tomorrow ", "in Pune ", "will be clear."]
    assert gateway.last_call_metrics is not None
    assert gateway.last_call_metrics["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_fallback_on_429_rate_limit(caplog: pytest.LogCaptureFixture) -> None:
    """When Groq returns 429 Too Many Requests, gateway falls back to OpenRouter."""
    def groq_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            json={"error": {"message": "Rate limit reached", "type": "tokens"}},
        )

    def openrouter_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_openrouter_1",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Fallback response from OpenRouter",
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 40,
                    "completion_tokens": 10,
                    "total_tokens": 50,
                },
            },
        )

    groq_client = httpx.AsyncClient(transport=httpx.MockTransport(groq_handler))
    openrouter_client = httpx.AsyncClient(transport=httpx.MockTransport(openrouter_handler))

    primary = OpenAICompatibleLLMAdapter(
        base_url="https://api.groq.com/openai/v1",
        api_key="mock-groq-key",
        model="llama-3.3-70b-versatile",
        provider_name="groq",
        client=groq_client,
    )
    fallback = OpenAICompatibleLLMAdapter(
        base_url="https://openrouter.ai/api/v1",
        api_key="mock-openrouter-key",
        model="meta-llama/llama-3.3-70b-instruct",
        provider_name="openrouter",
        client=openrouter_client,
    )
    gateway = LLMGateway(primary=primary, fallback=fallback)

    with caplog.at_level(logging.WARNING):
        res = await gateway.complete(messages=[{"role": "user", "content": "Hello"}])

    assert res["content"] == "Fallback response from OpenRouter"
    assert gateway.last_call_metrics["provider"] == "openrouter"
    assert gateway.last_call_metrics["model"] == "meta-llama/llama-3.3-70b-instruct"

    # Verify fallback was logged
    assert any("llm_primary_failed" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_fallback_on_timeout(caplog: pytest.LogCaptureFixture) -> None:
    """When primary times out, gateway retries or falls back to OpenRouter."""
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Connection timed out after 10s")

    def openrouter_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl_or_timeout_fallback",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Recovered via OpenRouter",
                        }
                    }
                ],
            },
        )

    groq_client = httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler))
    openrouter_client = httpx.AsyncClient(transport=httpx.MockTransport(openrouter_handler))

    primary = OpenAICompatibleLLMAdapter(
        base_url="https://api.groq.com/openai/v1",
        api_key="mock-groq-key",
        model="llama-3.3-70b-versatile",
        provider_name="groq",
        client=groq_client,
        max_retries=1,
    )
    fallback = OpenAICompatibleLLMAdapter(
        base_url="https://openrouter.ai/api/v1",
        api_key="mock-openrouter-key",
        model="meta-llama/llama-3.3-70b-instruct",
        provider_name="openrouter",
        client=openrouter_client,
    )
    gateway = LLMGateway(primary=primary, fallback=fallback)

    with caplog.at_level(logging.WARNING):
        res = await gateway.complete(messages=[{"role": "user", "content": "Check weather"}])

    assert res["content"] == "Recovered via OpenRouter"
    assert gateway.last_call_metrics["provider"] == "openrouter"
