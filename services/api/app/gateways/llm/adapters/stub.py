"""Stub LLM Adapter for testing and offline environments."""
from __future__ import annotations

import re
from typing import Any, AsyncGenerator

from services.api.app.gateways.llm.adapters.base import LLMAdapter


class StubLLMAdapter(LLMAdapter):
    def __init__(self, provider_name: str = "stub", model: str = "stub-model") -> None:
        self.provider_name = provider_name
        self.model = model
        self.last_call_metrics: dict[str, Any] = {
            "provider": provider_name,
            "model": model,
            "latency_ms": 10,
            "prompt_tokens": 15,
            "completion_tokens": 15,
            "total_tokens": 30,
        }

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any] | AsyncGenerator[str, None]:
        user_msg = messages[-1].get("content", "") if messages else ""
        sys_msg = messages[0].get("content", "") if messages and messages[0].get("role") == "system" else ""

        # Check if tools are requested and tool calls need to be made
        if tools and ("Pune" in user_msg or "कल" in user_msg or "rain" in user_msg.lower()):
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
                            "arguments": '{"place": "Pune", "day": 1}',
                        },
                    }
                ],
            }

        # Detect language code requested
        lang = "en"
        m_lang = re.search(r"language code '([a-z]{2})'", sys_msg)
        if m_lang:
            lang = m_lang.group(1)

        # Parse place from user_msg
        place = "Pune"
        m_place = re.search(r"Place:\s*([^\n,]+)", user_msg)
        if m_place:
            place = m_place.group(1).strip()

        # Parse chunk_id and guidance from advisory evidence packets if present
        m_chunk = re.search(r"'variable': 'chunk_id', 'value': '([^']+)'", user_msg)
        m_guidance = re.search(r"'variable': 'guidance', 'value': '([^']+)'", user_msg)
        if m_chunk and m_guidance:
            cid = m_chunk.group(1)
            guidance = m_guidance.group(1).replace("\\n", " ")
            if cid == "no_official_guidance":
                response_text = guidance
            else:
                if lang == "hi":
                    response_text = f"[{cid}] आधिकारिक दिशानिर्देश: {guidance}"
                else:
                    response_text = f"[{cid}] Official guidance: {guidance}"

            if stream:
                async def _stream_adv():
                    for word in response_text.split(" "):
                        yield word + " "
                return _stream_adv()

            return {
                "id": "stub_msg_1",
                "role": "assistant",
                "content": response_text,
                "tool_calls": None,
            }

        # Parse rain and temperature from evidence packets in user_msg if present
        rain_val = 0.0
        temp_val = 28.5
        m_rain = re.search(r"'variable': '(?:rain_sum|rain|precipitation_sum)', 'value': ([-+]?\d*\.?\d+)", user_msg)
        if m_rain:
            rain_val = float(m_rain.group(1))

        m_temp = re.search(r"'variable': '(?:tmax|temperature|temperature_2m_max)', 'value': ([-+]?\d*\.?\d+)", user_msg)
        if m_temp:
            temp_val = float(m_temp.group(1))

        if lang == "hi":
            response_text = f"Open-Meteo पूर्वानुमान के अनुसार कल {place} में बारिश {rain_val:.1f} मिमी और तापमान {temp_val:.1f} डिग्री रहेगा।"
        elif lang == "mr":
            response_text = f"Open-Meteo हवामान अंदाजानुसार उद्या {place} मध्ये पाऊस {rain_val:.1f} मिमी आणि तापमान {temp_val:.1f} अंश सेल्सिअस राहण्याची शक्यता आहे।"
        elif lang == "bn":
            response_text = f"Open-Meteo পূর্বাভাস অনুযায়ী আগামীকাল {place}-এ বৃষ্টিপাত {rain_val:.1f} মিমি এবং তাপমাত্রা {temp_val:.1f} ডিগ্রি সেলসিয়াস হতে পারে।"
        elif lang == "te":
            response_text = f"Open-Meteo సూచన ప్రకారం రేపు {place} లో వర్షం {rain_val:.1f} మి.మీ మరియు ఉష్ణోగ్రత {temp_val:.1f} డిగ్రీల సెల్సియస్ ఉండే అవకాశం ఉంది."
        elif lang == "ta":
            response_text = f"Open-Meteo வானிலை முன்னறிவிப்பின்படி நாளை {place} இல் மழை {rain_val:.1f} மிமீ மற்றும் வெப்பநிலை {temp_val:.1f} டிகிரி செல்சியஸ் பதிவாக வாய்ப்புள்ளது."
        elif lang == "or":
            response_text = f"Open-Meteo ପୂର୍ବାନୁମାନ ଅନୁଯାୟୀ ଆସନ୍ତାକାଲି {place} ରେ ବର୍ଷା {rain_val:.1f} ମିମି ଏବଂ ତାପମାତ୍ରା {temp_val:.1f} ଡିଗ୍ରୀ ସେଲସିୟସ ରହିପାରେ।"
        else:
            response_text = f"According to Open-Meteo forecasts, tomorrow in {place} expects {rain_val:.1f} mm rain and a temperature of {temp_val:.1f} degC."

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
