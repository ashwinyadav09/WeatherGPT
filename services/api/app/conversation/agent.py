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
from services.api.app.modules.advisory.engine import AdvisoryEngine
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
        advisory_engine: AdvisoryEngine | None = None,
    ) -> None:
        self.llm = llm or LLMGateway()
        self.forecast_service = forecast_service or ForecastService()
        self.location_resolver = location_resolver or LocationResolver()
        self.advisory_engine = advisory_engine or AdvisoryEngine()
        self.pending_clarifications: dict[str, dict[str, Any]] = {}

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

        # Safety Check 1: Evacuate-or-stay questions
        if AdvisoryEngine.is_evacuation_query(req.text):
            redirect = AdvisoryEngine.get_evacuation_redirect(lang)
            yield {
                "event": "card",
                "data": {
                    "headline": redirect["headline"],
                    "source_line": redirect["source_line"],
                    "caveat": "Official Safety Directive: Local authorities decide evacuation",
                    "style": "guidance-card",
                    "actions": ["112 (Emergency)", "1077 (Disaster)"],
                },
            }
            yield {"event": "token", "data": {"text": redirect["text"]}}
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

        # Safety Check 2: Pesticide dose questions
        if AdvisoryEngine.is_pesticide_dose_query(req.text):
            redirect = AdvisoryEngine.get_pesticide_redirect(lang)
            yield {
                "event": "card",
                "data": {
                    "headline": redirect["headline"],
                    "source_line": redirect["source_line"],
                    "caveat": "Safety Policy: Chemical dosages not prescribed",
                    "style": "guidance-card",
                    "actions": ["1800-180-1551 (Kisan Call Centre)"],
                },
            }
            yield {"event": "token", "data": {"text": redirect["text"]}}
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

        clean_text = req.text.strip().lower()

        # Check for confirmation/denial of pending place clarification
        confirmed_place = None
        if req.session_id in self.pending_clarifications:
            pending = self.pending_clarifications[req.session_id]
            if clean_text in ("हाँ", "हां", "yes", "sahi", "सही", "ha", "haan", "yep", "sure", "correct"):
                confirmed_place = pending["place"]
                del self.pending_clarifications[req.session_id]
            elif clean_text in ("नहीं", "ना", "no", "nahi", "nahin", "wrong", "गलत"):
                del self.pending_clarifications[req.session_id]
                prompt_msg = (
                    "कृपया अपने जिले या राज्य का नाम बताएं।"
                    if lang == "hi"
                    else "Please specify your district or state name."
                )
                yield {
                    "event": "card",
                    "data": {
                        "headline": "स्थान स्पष्ट करें" if lang == "hi" else "Location needed",
                        "source_line": "WeatherGPT Location Resolver",
                        "caveat": prompt_msg,
                    },
                }
                yield {"event": "token", "data": {"text": prompt_msg}}
                yield {"event": "done", "data": {}}
                return

        # 2. Resolve place and get forecast evidence
        if confirmed_place:
            place = confirmed_place
        else:
            resolved = await self.location_resolver.resolve(req.text, language=lang)
            if resolved.get("ambiguous") and resolved.get("clarification_question"):
                clarify_q = str(resolved["clarification_question"])
                cand_place = resolved.get("resolved_place")
                self.pending_clarifications[req.session_id] = {
                    "place": cand_place,
                    "places": resolved.get("places", []),
                    "language": lang,
                }
                actions = ["हाँ", "नहीं"] if lang == "hi" else ["Yes", "No"]
                yield {
                    "event": "card",
                    "data": {
                        "headline": "Clarification needed" if lang != "hi" else "स्थान स्पष्ट करें",
                        "source_line": "WeatherGPT Location Resolver",
                        "caveat": clarify_q,
                        "actions": actions,
                        "needs_confirmation": True,
                    },
                }
                yield {"event": "token", "data": {"text": clarify_q}}
                yield {"event": "done", "data": {}}
                return

            place = resolved.get("resolved_place")
        p_name = place.names.get(lang, place.names.get("en", "Pune")) if place else "Pune"
        lat = place.lat if place else 18.5204
        lon = place.lon if place else 73.8567

        # 2b. Check for Marine / Coastal query
        marine_terms = ["marine", "coastal bulletin", "fishermen warning", "sea condition", "समुद्र", "तटीय बुलेटिन", "मछुआरे", "मछुआरों", "लहरें"]
        if any(k in req.text.lower() for k in marine_terms):
            target_area = place.id if place else req.text
            marine_data = await self.advisory_engine.marine_adapter.get_marine_bulletin(area=target_area, language=lang)
            fw = marine_data.get("fishermen_warning", {})
            w_text = fw.get("warning_hi" if lang == "hi" else "warning_en", "")
            banner_txt = marine_data.get("safety_banner", {}).get("text_hi" if lang == "hi" else "text_en", "")
            marine_card_data = {
                "headline": f"Coastal Bulletin: {marine_data.get('area_name')}" if lang != "hi" else f"तटीय बुलेटिन: {marine_data.get('area_name')}",
                "key_values": {
                    "Sea Condition": marine_data.get("sea_condition", "Moderate"),
                    "Wind": marine_data.get("wind", ""),
                    "Weather": marine_data.get("weather", ""),
                },
                "source_line": f"Source: {marine_data.get('source')} (Official Warning)",
                "caveat": banner_txt,
                "style": "guidance-card",
                "actions": ["Official IMD Marine Bulletin", "INCOIS Advisories"],
                "marine_data": marine_data,
            }
            yield {"event": "card", "data": marine_card_data}
            ans_text = f"{marine_card_data['headline']} - {marine_data.get('weather')}. {w_text} {banner_txt}"
            yield {"event": "token", "data": {"text": ans_text}}
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

        # 2c. Check for Agromet / Farming query (Wheat / Rice / Crops)
        agro_terms = ["agromet", "wheat", "rice", "paddy", "गेहूं", "धान", "फसल", "crop", "sowing", "बुवाई", "कटाई", "रोपाई", "kheti", "कृषि"]
        if any(k in req.text.lower() for k in agro_terms):
            target_district = place.names.get("en", place.id) if place else "Ludhiana"
            crop = "rice" if any(r in req.text.lower() for r in ["rice", "paddy", "धान", "चावल", "dhan"]) else "wheat"
            agro_data = await self.advisory_engine.agromet_adapter.get_agromet_advisory(
                district=target_district,
                crop=crop,
                stage=req.text,
                language=lang,
                query_text=req.text,
            )
            if agro_data.get("status") == "refused_pesticide_dose":
                redirect = agro_data["redirect"]
                yield {
                    "event": "card",
                    "data": {
                        "headline": redirect["headline"],
                        "source_line": redirect["source_line"],
                        "caveat": "Safety Policy: Chemical dosages not prescribed",
                        "style": "guidance-card",
                        "actions": ["1800-180-1551 (Kisan Call Centre)"],
                    },
                }
                yield {"event": "token", "data": {"text": redirect["text"]}}
                latency_ms = int((time.time() - start_time) * 1000)
                yield {"event": "done", "data": {"latency_ms": latency_ms}}
                return

            agro_card_data = {
                "headline": (
                    f"IMD Agromet: {agro_data.get('crop_display')} ({agro_data.get('stage_display')})"
                    if lang != "hi"
                    else f"मौसम कृषि सलाह: {agro_data.get('crop_display')} ({agro_data.get('stage_display')})"
                ),
                "key_values": {
                    "District": agro_data.get("district", ""),
                    "Crop": agro_data.get("crop_display", ""),
                    "Stage": agro_data.get("stage_display", ""),
                },
                "source_line": f"Source: {agro_data.get('source')} | Issued: {agro_data.get('issue_date')}",
                "caveat": agro_data.get("safety_note", ""),
                "style": "guidance-card",
                "actions": ["KVK Guidance", "1800-180-1551 (Kisan Call Centre)"],
                "agromet_data": agro_data,
            }
            yield {"event": "card", "data": agro_card_data}
            ans_text = f"{agro_data.get('advisory_text', '')} {agro_data.get('safety_note', '')}"
            yield {"event": "token", "data": {"text": ans_text}}
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

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
            from services.api.app.modules.admin.service import admin_service
            g_terms = admin_service.get_glossary("hi").get("terms", {})
            rain_word = g_terms.get("rain", "बारिश")
            rf_phrase = get_hindi_rainfall_phrase(rain_val)
            if rain_word != "बारिश" and "बारिश" in rf_phrase:
                rf_phrase = rf_phrase.replace("बारिश", rain_word)
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
        elif lang == "mr":
            answer_text = (
                f"{source_display} हवामान अंदाजानुसार उद्या {p_name} मध्ये पाऊस {rain_val:.1f} मिमी आणि तापमान {temp_val:.1f} अंश सेल्सिअस राहण्याची शक्यता आहे। "
                "कृपया लक्षात घ्या की अधिकृत आयएमडी (IMD) अंदाज या पायलटमध्ये अद्याप थेट जोडलेला नाही (not connected)."
            )
        elif lang == "bn":
            answer_text = (
                f"{source_display} পূর্বাভাস অনুযায়ী আগামীকাল {p_name}-এ বৃষ্টিপাত {rain_val:.1f} মিমি এবং তাপমাত্রা {temp_val:.1f} ডিগ্রি সেলসিয়াস হতে পারে। "
                "অনুগ্রহ করে মনে রাখবেন যে সরকারি আইএমডি (IMD) পূর্বাভাস এই পাইলটে সরাসরি যুক্ত নয় (not connected)।"
            )
        elif lang == "te":
            answer_text = (
                f"{source_display} సూచన ప్రకారం రేపు {p_name} లో వర్షం {rain_val:.1f} మి.మీ మరియు ఉష్ణోగ్రత {temp_val:.1f} డిగ్రీల సెల్సియస్ ఉండే అవకాశం ఉంది. "
                "గమనిక: అధికారిక IMD సూచన ఈ పైలట్‌లో ఇంకా కనెక్ట్ కాలేదు (not connected)."
            )
        elif lang == "ta":
            answer_text = (
                f"{source_display} வானிலை முன்னறிவிப்பின்படி நாளை {p_name} இல் மழை {rain_val:.1f} மிமீ மற்றும் வெப்பநிலை {temp_val:.1f} டிகிரி செல்சியஸ் பதிவாக வாய்ப்புள்ளது. "
                "குறிப்பு: அதிகாரப்பூர்வ IMD முன்னறிவிப்பு இந்த பைலட்டில் நேரடியாக இணைக்கப்படவில்லை (not connected)."
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
        elif lang == "mr":
            headline = f"{p_name} हवामान अंदाज"
            key_values = {
                "पाऊस": f"{rain_val:.1f} मिमी",
                "तापमान": f"{temp_val:.1f} अंश सेल्सिअस",
            }
            caveat = "अधिकृत आयएमडी अंदाज थेट जोडलेला नाही"
            actions = ["तासनिहाय अंदाज", "इशारे पहा"]
        elif lang == "bn":
            headline = f"{p_name}-এর আবহাওয়া"
            key_values = {
                "বৃষ্টি": f"{rain_val:.1f} মিমি",
                "तापমাত্রা": f"{temp_val:.1f} ডিগ্রি সেলসিয়াস",
            }
            caveat = "সরকারি আইएमডি পূর্বাভাস সংযুক্ত নয়"
            actions = ["ঘণ্টায় পূর্বাভাস", "সতর্কতা দেখুন"]
        elif lang == "te":
            headline = f"{p_name} వాతావరణ సమాచారం"
            key_values = {
                "వర్షం": f"{rain_val:.1f} మి.మీ",
                "ఉష్ణోగ్రత": f"{temp_val:.1f} డిగ్రీలు",
            }
            caveat = "అధికారిక IMD సూచన ఇంకా కనెక్ట్ కాలేదు"
            actions = ["గంటల వారీ సమాచారం", "హెచ్చరికలు"]
        elif lang == "ta":
            headline = f"{p_name} வானிலை முன்னறிவிப்பு"
            key_values = {
                "மழை": f"{rain_val:.1f} மிமீ",
                "வெப்பநிலை": f"{temp_val:.1f} டிகிரி செல்சியஸ்",
            }
            caveat = "அதிகாரப்பூர்வ IMD முன்னறிவிப்பு இணைக்கப்படவில்லை"
            actions = ["மணிநேர முன்னறிவிப்பு", "எச்சரிக்கைகள்"]
        else:
            headline = f"Weather in {p_name}"
            key_values = {
                "Rain": f"{rain_val:.1f} mm",
                "Temperature": f"{temp_val:.1f} degC",
            }
            caveat = "Official IMD forecast is not connected"
            actions = ["View Hourly", "Set Alert"]

        # Check for active official warnings and attach guidance cards if applicable
        active_guidance = await self.advisory_engine.get_advisory(
            place_id=place.id if place else "pune",
            domain="heat_wave" if temp_val >= 35 else "cold_wave",
            language=lang,
        )

        card_data: dict[str, Any] = {
            "headline": headline,
            "key_values": key_values,
            "source_line": f"Data: {source_display} (CC BY 4.0)",
            "caveat": caveat,
            "actions": actions,
        }
        if active_guidance:
            card_data["guidance_cards"] = active_guidance

        yield {
            "event": "card",
            "data": card_data,
        }

        # 9. Stream done event
        latency_ms = int((time.time() - start_time) * 1000)
        yield {
            "event": "done",
            "data": {
                "latency_ms": latency_ms,
            },
        }
