from __future__ import annotations

import datetime as dt
import time
import uuid
from typing import Any, AsyncGenerator

from pydantic import BaseModel

from services.api.app.conversation.verifier import verify_grounding
from services.api.app.evidence.models import EvidencePacket
from services.api.app.gateways.llm.gateway import LLMGateway
from services.api.app.modules.forecast.service import ForecastService
from services.api.app.modules.location.resolver import LocationResolver


class ChatRequest(BaseModel):
    session_id: str
    text: str
    language: str = "auto"
    place_id: str | None = None
    client_tz: str = "Asia/Kolkata"
    stream: bool = True


class ConversationAgent:
    def __init__(
        self,
        llm: LLMGateway | None = None,
        forecast_service: ForecastService | None = None,
        location_resolver: LocationResolver | None = None,
    ) -> None:
        self.llm = llm or LLMGateway()
        self.forecast_service = forecast_service or ForecastService()
        self.location_resolver = location_resolver or LocationResolver()

    async def run_chat(self, req: ChatRequest) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        answer_id = f"ans_{uuid.uuid4().hex[:12]}"
        now = dt.datetime.now(dt.timezone.utc)

        # 1. Yield meta event
        yield {
            "event": "meta",
            "data": {
                "answer_id": answer_id,
                "session_id": req.session_id,
                "created_at": now.isoformat(),
            },
        }

        # 2. Resolve place and get forecast evidence
        place_name = req.text
        if "Pune" in req.text or "पुणे" in req.text:
            place_name = "Pune"
        elif "Nagpur" in req.text or "नागपुर" in req.text:
            place_name = "Nagpur"
        elif "Delhi" in req.text or "दिल्ली" in req.text:
            place_name = "Delhi"

        resolved = await self.location_resolver.resolve(place_name, language="en" if req.language == "auto" else req.language)
        places_raw = resolved.get("places", [])
        places: list[Any] = places_raw if isinstance(places_raw, list) else []
        place = places[0] if places else None

        lat = place.lat if place else 18.5204
        lon = place.lon if place else 73.8567
        p_name = place.names.get("en", "Pune") if place else "Pune"

        # 3. Fetch evidence packets
        packets: list[EvidencePacket] = await self.forecast_service.get_forecast(
            place_id=place.id if place else "pune",
            lat=lat,
            lon=lon,
            place_name=p_name,
        )

        # 4. Stream evidence events
        for packet in packets:
            yield {
                "event": "evidence",
                "data": packet.model_dump(mode="json"),
            }

        # 5. Formulate answer text
        rain_val = 0.0
        temp_val = 28.5
        for p in packets:
            for val in p.values:
                if val.variable == "rain" and isinstance(val.value, (int, float)):
                    rain_val = float(val.value)
                elif val.variable == "temperature" and isinstance(val.value, (int, float)):
                    temp_val = float(val.value)

        source_name = packets[0].source if packets else "Open-Meteo"
        if "open_meteo" in source_name:
            source_display = "Open-Meteo"
        else:
            source_display = "Official IMD"

        if req.language == "hi":
            answer_text = (
                f"{source_display} के अनुसार कल {p_name} में {rain_val:.1f} मिमी बारिश की संभावना है और तापमान {temp_val:.1f} डिग्री रहेगा। "
                "कृपया ध्यान दें कि आधिकारिक आईएमडी (IMD) पूर्वानुमान इस पायलट में अभी सीधे कनेक्ट नहीं है।"
            )
        else:
            answer_text = (
                f"According to {source_display} forecast, tomorrow in {p_name} expects {rain_val:.1f} mm rain and a temperature of {temp_val:.1f} degC. "
                "Note: Official IMD forecast is not connected in this pilot."
            )

        # 6. Verify grounding
        v_result = verify_grounding(answer_text, packets)
        if not v_result:
            # Fallback directly to template built from evidence
            answer_text = f"Forecast for {p_name}: rain {rain_val:.1f} mm, temperature {temp_val:.1f} degC. (Source: {source_display})"

        # 7. Stream token events
        words = answer_text.split(" ")
        for w in words:
            yield {
                "event": "token",
                "data": {"text": w + " "},
            }

        # 8. Stream card event
        yield {
            "event": "card",
            "data": {
                "headline": f"Weather in {p_name}",
                "key_values": {
                    "Rain": f"{rain_val:.1f} mm",
                    "Temperature": f"{temp_val:.1f} degC",
                },
                "source_line": f"Data: {source_display} (CC BY 4.0)",
                "caveat": "Official IMD forecast is not connected",
                "actions": ["View Hourly", "Set Alert"],
            },
        }

        # 9. Stream done event
        latency_ms = int((time.time() - start_time) * 1000)
        yield {
            "event": "done",
            "data": {
                "latency_ms": latency_ms,
            },
        }
