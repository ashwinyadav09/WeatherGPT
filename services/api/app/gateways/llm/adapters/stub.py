from __future__ import annotations

from typing import Any, AsyncGenerator

from services.api.app.gateways.llm.adapters.base import LLMAdapter


class StubLLMAdapter(LLMAdapter):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        # If user asked a question, stub can either return tool call or response
        user_msg = messages[-1].get("content", "") if messages else ""

        # Check if tools are requested and tool calls need to be made
        if tools and ("Pune" in user_msg or "कल" in user_msg or "rain" in user_msg.lower()):
            # Return tool call for get_forecast
            return {
                "id": "stub_call_1",
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "get_forecast",
                            "arguments": '{"place_id": "pune", "start": "2026-11-18T00:00:00Z", "end": "2026-11-19T00:00:00Z"}',
                        },
                    }
                ],
            }

        response_text = (
            "According to Open-Meteo forecasts, light rain of around 0 mm is expected tomorrow in Pune."
        )

        if stream:
            async def _stream():
                for word in response_text.split(" "):
                    yield word + " "
            return _stream()

        return {
            "id": "stub_msg_1",
            "role": "assistant",
            "content": response_text,
            "tool_calls": None,
        }
