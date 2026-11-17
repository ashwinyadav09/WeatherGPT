from __future__ import annotations

import datetime as dt
import time
import uuid
from typing import Any, AsyncGenerator

from pydantic import BaseModel

from services.api.app.conversation.i18n import (
    check_hindi_glossary,
    detect_language,
    get_hindi_rainfall_phrase,
)
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

        # Determine language (auto-detect if auto or not provided)
        lang = req.language
        if not lang or lang == "auto":
            lang = detect_language(req.text)

        # 2. Resolve place and get forecast evidence
        from services.api.app.modules.location.resolver import SEED_PLACES
        place = None
        p_name = "Pune"
        for sp in SEED_PLACES:
            if any(n.lower() in req.text.lower() for n in sp.names.values()):
                place = sp
                p_name = sp.names.get(lang, sp.names.get("en", sp.id.title()))
                break

        if not place:
            resolved = await self.location_resolver.resolve(req.text, language=lang)
            places_raw = resolved.get("places", [])
            places: list[Any] = places_raw if isinstance(places_raw, list) else []
            place = places[0] if places else None
            p_name = place.names.get(lang, place.names.get("en", "Pune")) if place else "Pune"

        lat = place.lat if place else 18.5204
        lon = place.lon if place else 73.8567

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

        if lang == "hi":
            rf_phrase = get_hindi_rainfall_phrase(rain_val)
            rain_phrase = f"{rf_phrase} ({rain_val:.1f} मिमी)"
            answer_text = (
                f"{source_display} पूर्वानुमान के अनुसार कल {p_name} में {rain_phrase} की संभावना है "
                f"और तापमान {temp_val:.1f} डिग्री रहेगा। "
                "कृपया ध्यान दें कि आधिकारिक आईएमडी (IMD) पूर्वानुमान इस पायलट में अभी सीधे कनेक्ट नहीं है।"
            )
            # Run glossary check
            glossary_res = check_hindi_glossary(answer_text)
            if not glossary_res.is_valid:
                answer_text = (
                    f"{source_display} पूर्वानुमान: {p_name} में कल बारिश {rain_val:.1f} मिमी, तापमान {temp_val:.1f} डिग्री रहेगा। "
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
            if lang == "hi":
                answer_text = (
                    f"{source_display} पूर्वानुमान: {p_name} में कल बारिश {rain_val:.1f} मिमी, तापमान {temp_val:.1f} डिग्री रहेगा। "
                    "कृपया ध्यान दें कि आधिकारिक आईएमडी (IMD) पूर्वानुमान इस पायलट में अभी सीधे कनेक्ट नहीं है।"
                )
            else:
                answer_text = (
                    f"According to {source_display} forecast for {p_name}: rain {rain_val:.1f} mm, "
                    f"temperature {temp_val:.1f} degC. Note: Official IMD forecast is not connected in this pilot."
                )

        # 7. Stream token events
        words = answer_text.split(" ")
        for w in words:
            yield {
                "event": "token",
                "data": {"text": w + " "},
            }

        # 8. Stream card event
        if lang == "hi":
            headline = f"{p_name} का मौसम"
            key_values = {
                "बारिश": f"{rain_val:.1f} मिमी",
                "तापमान": f"{temp_val:.1f} डिग्री",
            }
            caveat = "आधिकारिक आईएमडी पूर्वानुमान कनेक्ट नहीं है"
            actions = ["प्रति घंटा देखें", "अलर्ट सेट करें"]
        else:
            headline = f"Weather in {p_name}"
            key_values = {
                "Rain": f"{rain_val:.1f} mm",
                "Temperature": f"{temp_val:.1f} degC",
            }
            caveat = "Official IMD forecast is not connected"
            actions = ["View Hourly", "Set Alert"]

        yield {
            "event": "card",
            "data": {
                "headline": headline,
                "key_values": key_values,
                "source_line": f"Data: {source_display} (CC BY 4.0)",
                "caveat": caveat,
                "actions": actions,
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
