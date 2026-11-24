"""Conversational Orchestrator for WeatherGPT (Ticket R2.3 & R2.4).

Replaces fixed f-string template agent with a tool-calling, grounded, and verified orchestrator.
- Safety pre-guards stay first (evacuation, pesticide dose).
- Aviation queries politely refused (decision D3).
- Deterministic routing when intent is confident, LLM tool-calling otherwise.
- Uses agent tools (geocode, get_forecast, get_alerts, get_climate, search_knowledge).
- Grounding verification: on ungrounded numbers, retries once, then falls back to vetted template.
- Emits SSE events: meta, evidence, token, card, trace (R2.4), done.
- Session context (place, target date) with TTL and zero personal data.
"""
from __future__ import annotations

import datetime as dt
import logging
import time
import uuid
from typing import Any, AsyncGenerator

from pydantic import BaseModel

from services.api.app.agent.tools import (
    get_alerts,
    get_climate,
    get_forecast,
    get_risk_outlook,
    search_knowledge,
)
from services.api.app.conversation.i18n import (
    detect_language,
    get_hindi_rainfall_phrase,
)
from services.api.app.conversation.verifier import extract_numbers_from_text, verify_grounding
from services.api.app.evidence.models import EvidencePacket, PlaceReference
from services.api.app.gateways.llm.gateway import LLMGateway
from services.api.app.gateways.translation.gateway import TranslationGateway
from services.api.app.modules.advisory.engine import AdvisoryEngine
from services.api.app.modules.alerts.engine import AlertEngine
from services.api.app.modules.climate.service import ClimateService
from services.api.app.modules.forecast.service import ForecastService
from services.api.app.modules.location.data import PLACES_BY_ID
from services.api.app.modules.location.resolver import LocationResolver

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 900  # 15 minutes

ADVISORY_TITLES: dict[str, str] = {
    "en": "Safety & Weather Advisory",
    "hi": "मौसम व सुरक्षा सलाह",
    "bn": "আবহাওয়া ও সুরক্ষা সংক্রান্ত পরামর্শ",
    "mr": "हवामान आणि सुरक्षा सल्ला",
    "te": "వాతావరణ మరియు భద్రతా సలహా",
    "ta": "வானிலை மற்றும் பாதுகாப்பு ஆலோசனை",
    "or": "ପାଣିପାଗ ଏବଂ ସୁରକ୍ଷା ପରାମର୍ଶ",
}

HAZARD_ADVISORY_TERMS: tuple[str, ...] = (
    # Lightning / thunderstorm
    "lightning", "thunderstorm", "बिजली", "आकाशीय बिजली", "तूफान", "वज्रपात", "तड़ित",
    "বজ্রপাত", "বজ্রঝড়", "विजांचा", "कडकडाट", "वादळ", "वादळाच्या", "ఉరుములు", "మెరుపులు", "మెరుపుల",
    "இடி", "மின்னல்", "புயல்", "புயலின்", "ବଜ୍ରପାତ", "ଝଡ଼",
    # Heatwave
    "heatwave", "heat wave", "लू", "भीषण लू", "तापদাহ", "উष्णतेच्या", "उष्णतेची लाट",
    "వడగాల్పులు", "వడగాల్పుల", "வெப்ப அலை", "ଗ୍ରୀଷ୍ମ ପ୍ରବାହ",
    # Coldwave
    "coldwave", "cold wave", "शीतलहर", "ठंड", "শৈত্যপ্রবাহ", "शीत लाट", "थंडीची लाट", "थंडीच्या",
    "శీతల గాలులు", "శీతల గాలుల", "குளிர்கால", "ଶୀତ ଲହରୀ",
    # Flood
    "flood", "waterlogging", "बाढ़", "বন্যা", "पूर", "వరదలు", "வெள்ளம்", "ବନ୍ୟା",
    # Cyclone
    "cyclone", "चक्रवात", "ঘূর্ণিঝড়", "चक्रीवादळ", "తుఫాను", "சூறாவளி", "ବାତ୍ୟା", "ଚକ୍ରବାତ",
    # Crop protection / agriculture advisory
    "crop protection", "crop safety", "agriculture advisory", "फसल सुरक्षा", "फसलों की सुरक्षा",
    "कृषि सलाह", "ফসল সুরক্ষা", "কৃষি পরামর্শ", "पीक संरक्षण", "पिकांची काळजी", "पिकांच्या",
    "कृषी सल्ला", "పంటల రక్షణ", "పంటల జాగ్రత్తలు", "వ్యవసాయ సలహా", "பயிர் பாதுகாப்பு",
    "பயிர்களை", "வேளாண் ஆலோசனை", "ଫସଲ ସୁରକ୍ଷା", "କୃଷି ପରାମର୍ଶ",
    # General safety / advice keywords
    "safety rules", "precautions", "do's and don'ts", "सावधानियां", "सुरक्षा नियम",
    "बचाव के उपाय", "निরাপত্তা নিয়ম", "সতর্কতা", "काळजी",
    "రక్షణ చర్యలు", "జాగ్రత్తలు", "பாதுகாப்பு விதிகள்", "முன்னெச்சரிக்கை", "ନିରାପତ୍ତା ନିୟମ",
)


_RISK_OVERRIDE_TERMS: tuple[str, ...] = (
    "risk outlook", "risk", "extreme event", "extreme heatwave risk", "extreme heat risk",
    "extreme cold risk", "flood risk", "cyclone risk", "risk forecast", "risk prediction",
    "risk assessment", "जोखिम", "खतरा", "ریسک",
)


def is_hazard_or_advice_query(text: str) -> bool:
    """Detect if query asks for hazard safety, warnings, or advisory guidelines (Ticket R20.5).

    Returns False for queries that are risk/outlook queries even if they mention a hazard
    term (e.g. "extreme heatwave risk outlook" is a risk forecast, not a safety advisory).
    """
    text_lower = text.lower()
    # Risk/outlook queries take priority: even if a hazard term appears, they route to risk intent
    if any(rt in text_lower for rt in _RISK_OVERRIDE_TERMS):
        return False
    return any(term in text_lower for term in HAZARD_ADVISORY_TERMS)



class ChatRequest(BaseModel):
    session_id: str
    text: str
    language: str = "auto"
    place_id: str | None = None
    client_tz: str = "Asia/Kolkata"
    stream: bool = True
    ml_mode: str = "raw"  # "raw" | "ml"


def is_model_enabled(model_name: str) -> bool:
    """Check whether a model is enabled in production from its audited reports/metrics.json."""
    from pathlib import Path
    metrics_path = Path(__file__).resolve().parents[4] / "ml" / model_name / "reports" / "metrics.json"
    if not metrics_path.exists():
        return False
    try:
        import json
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        return bool(data.get("enabled_in_production", True))
    except Exception:
        return False


_DEFAULT_INTENT = object()


class Orchestrator:
    def __init__(
        self,
        llm: LLMGateway | None = None,
        forecast_service: ForecastService | None = None,
        location_resolver: LocationResolver | None = None,
        alert_engine: AlertEngine | None = None,
        advisory_engine: AdvisoryEngine | None = None,
        climate_service: ClimateService | None = None,
        translation_gateway: TranslationGateway | None = None,
        llm_gateway: LLMGateway | None = None,
        intent_model: Any = _DEFAULT_INTENT,
    ) -> None:
        self.llm = llm or llm_gateway or LLMGateway()
        self.forecast_service = forecast_service or ForecastService()
        self.location_resolver = location_resolver or LocationResolver()
        self.alert_engine = alert_engine or AlertEngine()
        self.advisory_engine = advisory_engine or AdvisoryEngine()
        self.climate_service = climate_service or ClimateService()
        self.translation_gateway = translation_gateway
        if intent_model is not _DEFAULT_INTENT:
            self.intent_model = intent_model
        else:
            try:
                from ml.intent.service import IntentService
                self.intent_model = IntentService()
            except Exception:
                self.intent_model = None
        self.sessions: dict[str, dict[str, Any]] = {}
        self.pending_clarifications: dict[str, dict[str, Any]] = {}

    def _prune_sessions(self, now_ts: float) -> None:
        """Prune session contexts older than TTL."""
        expired = [
            sid
            for sid, sdata in self.sessions.items()
            if now_ts - sdata.get("last_seen", 0) > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            self.sessions.pop(sid, None)

    def _get_session_place(self, session_id: str) -> Any | None:
        sdata = self.sessions.get(session_id)
        if sdata:
            return sdata.get("place")
        return None

    def _update_session_place(self, session_id: str, place: Any) -> None:
        now_ts = time.time()
        self._prune_sessions(now_ts)
        if session_id not in self.sessions:
            self.sessions[session_id] = {}
        self.sessions[session_id]["place"] = place
        self.sessions[session_id]["last_seen"] = now_ts

    async def run_chat(self, req: ChatRequest) -> AsyncGenerator[dict[str, Any], None]:
        start_time = time.time()
        answer_id = f"ans_{uuid.uuid4().hex[:12]}"
        now = dt.datetime.now(dt.timezone.utc)

        # 1. Meta event
        yield {
            "event": "meta",
            "data": {
                "answer_id": answer_id,
                "session_id": req.session_id,
                "created_at": now.isoformat(),
            },
        }

        # Determine language
        lang = req.language
        if not lang or lang == "auto":
            lang = detect_language(req.text)

        # 2. Safety Pre-guard: Evacuation query
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
            yield {
                "event": "trace",
                "data": {
                    "intent": "safety_redirect",
                    "confidence": None,
                    "router_path": "safety_guard",
                    "tools": [],
                    "models": [],
                    "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                    "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                },
            }
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

        # 3. Safety Pre-guard: Pesticide dose query
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
            yield {
                "event": "trace",
                "data": {
                    "intent": "safety_redirect",
                    "confidence": None,
                    "router_path": "safety_guard",
                    "tools": [],
                    "models": [],
                    "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                    "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                },
            }
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

        # 4. Aviation briefing query (Decision D3: recognized and politely declined)
        aviation_terms = ["aviation", "metar", "taf", "aerodrome", "pilot briefing", "flight weather", "विमान", "விமானம்", "విమానం"]
        if any(term in req.text.lower() for term in aviation_terms):
            aviation_msgs = {
                "hi": "हवाई मौसम ब्रीफिंग (METAR/TAF) इस पायलट संस्करण में समर्थित नहीं है। आधिकारिक विमानन मौसम के लिए कृपया IMD विमानन पोर्टल देखें।",
                "bn": "বিমান চলাচল সংক্রান্ত আবহাওয়া ব্রিফिंग (METAR/TAF) এই পাইলট সংস্করণে সমর্থিত নয়। ফ্লাইট পরিকল্পনার জন্য অনুগ্রহ করে সরকারি বিমান চলাচল পোর্টাল দেখুন।",
                "mr": "विमान वाहतूक हवामान माहिती (METAR/TAF) या पायलट प्रकल्पात समर्थित नाही. कृपया अधिकृत विमान वाहतूक हवामान पोर्टलचा वापर करा.",
                "te": "విమానయాన వాతావరణ సమాచారం (METAR/TAF) ఈ పైలట్ ప్రాజెక్ట్‌లో అందుబాటులో లేదు. విమాన ప్రణాళిక కోసం దయచేసి అధికారిక పోర్టల్‌లను చూడండి.",
                "ta": "விமான வானிலை விவரங்கள் (METAR/TAF) இந்த முன்னோடி திட்டத்தில் ஆதரிக்கப்படவில்லை. விமான திட்டமிடலுக்கு அதிகாரப்பூர்வ வானிலை போர்ட்டலைப் பார்க்கவும்.",
                "or": "ବିମାନ ଚଳାଚଳ ପାଣିପାଗ ବିବରଣୀ (METAR/TAF) ଏହି ପାଇଲଟ୍ ପ୍ରକଳ୍ପରେ ସମର୍ଥିତ ନୁହେଁ। ବିମାନ ଯୋଜନା ପାଇଁ ଦୟାକରି ସରକାରୀ ବିମାନ ଚଳାଚଳ ପୋର୍ଟାଲ୍ ଦେଖନ୍ତୁ।",
            }
            msg = aviation_msgs.get(
                lang,
                "Aviation weather briefings (METAR/TAF) are not supported in this public-interest pilot. Please consult official aviation portals for flight planning."
            )
            yield {
                "event": "card",
                "data": {
                    "headline": "विमानन मौसम (Aviation Weather)" if lang == "hi" else "Aviation Weather",
                    "source_line": "WeatherGPT Policy: Non-commercial public pilot",
                    "caveat": msg,
                    "actions": ["IMD Aviation Weather"],
                    "category": "refusal",
                },
            }
            yield {"event": "token", "data": {"text": msg}}
            yield {
                "event": "trace",
                "data": {
                    "intent": "aviation_brief",
                    "confidence": None,
                    "router_path": "policy_check",
                    "tools": [],
                    "models": [],
                    "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                    "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                },
            }
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

        # 4b. Check for Marine / Coastal query
        marine_terms = ["marine", "coastal bulletin", "fishermen warning", "sea condition", "समुद्र", "तटीय बुलेटिन", "मछुआरे", "मछुआरों", "लहरें", "konkan"]
        if any(k in req.text.lower() for k in marine_terms):
            target_area = req.place_id or req.text
            marine_data = await self.advisory_engine.marine_adapter.get_marine_bulletin(area=target_area, language=lang)
            if marine_data.get("status") == "unavailable":
                area_title = marine_data.get("area_name", target_area.replace("_", " ").title())
                msg = (
                    f"{area_title} के लिए तटीय मौसम बुलेटिन वर्तमान में उपलब्ध नहीं है।"
                    if lang == "hi"
                    else f"Coastal weather bulletins are currently unavailable for {area_title}."
                )
                yield {
                    "event": "card",
                    "data": {
                        "headline": f"Coastal Bulletin: {area_title}" if lang != "hi" else f"तटीय बुलेटिन: {area_title}",
                        "source_line": "Source: Coastal Weather Services",
                        "caveat": msg,
                        "actions": ["INCOIS Advisories"],
                    },
                }
                yield {"event": "token", "data": {"text": msg}}
                yield {
                    "event": "trace",
                    "data": {
                        "intent": "advisory",
                        "confidence": None,
                        "router_path": "marine_adapter",
                        "tools": [{"name": "marine_bulletin", "args": {"area": target_area}, "latency_ms": 10}],
                        "models": [],
                        "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                        "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                    },
                }
                latency_ms = int((time.time() - start_time) * 1000)
                yield {"event": "done", "data": {"latency_ms": latency_ms}}
                return

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
                "actions": ["Marine Bulletin", "INCOIS Advisories"],
                "marine_data": marine_data,
            }
            yield {"event": "card", "data": marine_card_data}
            ans_text = f"{marine_card_data['headline']} - {marine_data.get('weather')}. {w_text} {banner_txt}"
            yield {"event": "token", "data": {"text": ans_text}}
            yield {
                "event": "trace",
                "data": {
                    "intent": "advisory",
                    "confidence": None,
                    "router_path": "marine_adapter",
                    "tools": [{"name": "marine_bulletin", "args": {"area": target_area}, "latency_ms": 10}],
                    "models": [],
                    "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                    "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                },
            }
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

        # 4c. Check for Agromet / Farming query (Wheat Sowing / Rice / Agromet)
        agro_terms = ["agromet", "wheat sowing", "धान की फसल", "गेहूं की बुवाई"]
        if any(k in req.text.lower() for k in agro_terms):
            target_district = None
            if req.place_id:
                target_district = req.place_id.replace("_", " ").title()
            else:
                # Extract place from text if available
                resolved_agro = await self.location_resolver.resolve(req.text, language=lang)
                if resolved_agro.get("resolved_place"):
                    target_district = resolved_agro["resolved_place"].names.get("en", resolved_agro["resolved_place"].id)

            if not target_district:
                prompt_msg = (
                    "कृपया अपने जिले का नाम बताएं ताकि संबंधित कृषि परामर्श दी जा सके।"
                    if lang == "hi"
                    else "Please specify your district for agricultural advisories."
                )
                yield {
                    "event": "card",
                    "data": {
                        "headline": "जिला स्पष्ट करें" if lang == "hi" else "District needed",
                        "source_line": "WeatherGPT Location Resolver",
                        "caveat": prompt_msg,
                    },
                }
                yield {"event": "token", "data": {"text": prompt_msg}}
                yield {
                    "event": "trace",
                    "data": {
                        "intent": "clarification",
                        "confidence": None,
                        "router_path": "location_resolver",
                        "tools": [],
                        "models": [],
                        "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                        "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                    },
                }
                latency_ms = int((time.time() - start_time) * 1000)
                yield {"event": "done", "data": {"latency_ms": latency_ms}}
                return

            crop = "rice" if any(r in req.text.lower() for r in ["rice", "paddy", "धान", "चावल", "dhan"]) else "wheat"
            agro_data = await self.advisory_engine.agromet_adapter.get_agromet_advisory(
                district=target_district,
                crop=crop,
                stage=req.text,
                language=lang,
                query_text=req.text,
            )
            if agro_data.get("status") == "unavailable":
                msg = (
                    f"कृषि मौसम परामर्श {target_district} के लिए वर्तमान में उपलब्ध नहीं है।"
                    if lang == "hi"
                    else f"Agromet weather advisories are currently unavailable for {target_district}."
                )
                yield {
                    "event": "card",
                    "data": {
                        "headline": "Agromet Advisory" if lang != "hi" else "कृषि परामर्श",
                        "source_line": "Source: Gramin Krishi Mausam Sewa",
                        "caveat": msg,
                        "actions": ["1800-180-1551 (Kisan Call Centre)"],
                    },
                }
                yield {"event": "token", "data": {"text": msg}}
                yield {
                    "event": "trace",
                    "data": {
                        "intent": "advisory",
                        "confidence": None,
                        "router_path": "agromet_adapter",
                        "tools": [{"name": "agromet_advisory", "args": {"district": target_district, "crop": crop}, "latency_ms": 10}],
                        "models": [],
                        "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                        "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                    },
                }
                latency_ms = int((time.time() - start_time) * 1000)
                yield {"event": "done", "data": {"latency_ms": latency_ms}}
                return

            agro_card_data = {
                "headline": (
                    f"Agromet Advisory: {agro_data.get('crop_display')} ({agro_data.get('stage_display')})"
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
            yield {
                "event": "trace",
                "data": {
                    "intent": "advisory",
                    "confidence": None,
                    "router_path": "agromet_adapter",
                    "tools": [{"name": "agromet_advisory", "args": {"district": target_district, "crop": crop}, "latency_ms": 10}],
                    "models": [],
                    "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                    "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                },
            }
            latency_ms = int((time.time() - start_time) * 1000)
            yield {"event": "done", "data": {"latency_ms": latency_ms}}
            return

        # Check if query is a hazard safety, advice, or advisory question (Ticket R20.5)
        # Hazard-safety and advice questions (lightning, thunderstorm, heatwave, cold wave,
        # flood, cyclone, crop protection) must route to the advisory path and never to place resolution.
        is_hazard_advisory = is_hazard_or_advice_query(req.text)
        place = None

        if is_hazard_advisory:
            # Hazard advisory queries do NOT geocode or resolve question text (Finding V5)
            if req.session_id in self.pending_clarifications:
                del self.pending_clarifications[req.session_id]
            if req.place_id:
                pid = req.place_id.lower()
                place = PLACES_BY_ID.get(pid)
            if not place:
                place = self._get_session_place(req.session_id)
            if place:
                p_name = place.names.get(lang, place.names.get("en", place.id))
                place_ref = PlaceReference(id=place.id, name=p_name, lat=place.lat, lon=place.lon)
            else:
                p_name = "India" if lang == "en" else "भारत"
                place_ref = PlaceReference(id="in_national", name=p_name, lat=20.5937, lon=78.9629)
        else:
            # 5. Place Resolution & Session Memory
            confirmed_place = None
            clean_text = req.text.strip().lower()
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
                    yield {
                        "event": "trace",
                        "data": {
                            "intent": "clarification",
                            "confidence": None,
                            "router_path": "location_resolver",
                            "tools": [],
                            "models": [],
                            "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                            "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                        },
                    }
                    latency_ms = int((time.time() - start_time) * 1000)
                    yield {"event": "done", "data": {"latency_ms": latency_ms}}
                    return

            if confirmed_place:
                place = confirmed_place
            elif req.place_id:
                pid = req.place_id.lower()
                place = PLACES_BY_ID.get(pid)
                if not place:
                    resolved_p = await self.location_resolver.resolve(req.place_id, language=lang)
                    place = resolved_p.get("resolved_place")
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
                    yield {
                        "event": "trace",
                        "data": {
                            "intent": "clarification",
                            "confidence": None,
                            "router_path": "location_resolver",
                            "tools": [{"name": "geocode", "args": {"text": req.text}, "latency_ms": 5, "source": "nominatim_or_gazetteer", "provenance": "cached"}],
                            "models": [],
                            "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                            "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                        },
                    }
                    latency_ms = int((time.time() - start_time) * 1000)
                    yield {"event": "done", "data": {"latency_ms": latency_ms}}
                    return

                place = resolved.get("resolved_place")

            # Fallback to session context if user didn't mention a new place
            if not place:
                place = self._get_session_place(req.session_id)

            if place:
                self._update_session_place(req.session_id, place)
                p_name = place.names.get(lang, place.names.get("en", place.id))
                lat = place.lat
                lon = place.lon
                place_ref = PlaceReference(id=place.id, name=p_name, lat=lat, lon=lon)
            else:
                prompt_msg = (
                    "कृपया अपने शहर या जिले का नाम बताएं।"
                    if lang == "hi"
                    else "Please specify your city or district."
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
                yield {
                    "event": "trace",
                    "data": {
                        "intent": "clarification",
                        "confidence": None,
                        "router_path": "location_resolver",
                        "tools": [],
                        "models": [],
                        "verifier": {"passed": True, "checked_numbers": [], "failures": []},
                        "llm": {"provider": "none", "model": "none", "tokens_in": 0, "tokens_out": 0},
                    },
                }
                latency_ms = int((time.time() - start_time) * 1000)
                yield {"event": "done", "data": {"latency_ms": latency_ms}}
                return

        # 6. Intent Routing & Tool Execution
        tools_executed: list[dict[str, Any]] = []
        evidence_packets: list[EvidencePacket] = []
        models_invoked: list[dict[str, Any]] = []
        confidence: float | None = None
        router_path: str = "deterministic"
        intent = "forecast"

        # Check if query is an advisory question that does not require a specific town/city
        advisory_keywords = [
            "heat wave", "heatwave", "cold wave", "coldwave", "drinking water", "लू", "ठंड", "शीतलहर", "do's and don'ts",
            "advice", "guidance", "guidelines", "ndma", "precaution", "what should i do", "safety", "उपाय", "सलाह", "बचाव",
            "crop", "wheat", "rice", "paddy", "farming", "sowing", "irrigation", "फसल", "कृषि", "सिंचाई", "बुवाई", "kheti", "धान", "गेहूं",
            "lightning", "बिजली", "आकाशीय बिजली", "तूफान", "thunderstorm",
            "colour code", "yellow warning", "orange alert", "red warning", "कलर कोड",
            "तापदाह", "শৈত্যপ্রবাহ", "বজ্রপাত", "পরামর্শ", "সতর্কতা",
            "उष्णतेच्या", "लाटेत", "विजांचा", "पिकांच्या", "काळजी",
            "వడగాల్పుల", "శీతల గాలుల", "ఉరుములు", "మెరుపుల", "పంటల", "జాగ్రత్తలు",
            "வெப்ப அலை", "குளிர்கால", "இடி மின்னல்", "பயிர்களை", "முன்னெச்சரிக்கை",
            "ଗ୍ରୀଷ୍ମ ପ୍ରବାହ", "ଶୀତ ଲହରୀ", "ବଜ୍ରପାତ", "ସତର୍କତା", "ଫସଲ", "କୃଷି", "ପରାମର୍ଶ", "ସୁରକ୍ଷା",
        ]

        if self.intent_model and is_model_enabled("intent"):
            try:
                try:
                    pred = self.intent_model.predict(req.text, language=lang)
                except TypeError:
                    pred = self.intent_model.predict(req.text)
                confidence = float(getattr(pred, "confidence", 0.0))
                auto_route = getattr(pred, "auto_route", False)
                m_id = getattr(self.intent_model, "MODEL_ID", "intent_classifier_v1.0")
                m_ver = getattr(self.intent_model, "MODEL_VERSION", "v1.0")
                models_invoked.append({"id": m_id, "version": m_ver, "used": True})

                if is_hazard_advisory:
                    intent = "advisory"
                    router_path = "intent_model_auto" if auto_route else "intent_model"
                elif auto_route and getattr(pred, "intent", None) not in (None, "out_of_domain"):
                    intent = pred.intent
                    router_path = "intent_model_auto"
                else:
                    # Query below auto-route threshold tau: fall back to keyword matching
                    router_path = "intent_model"
                    is_climate = any(w in req.text.lower() for w in ["climate", "normal", "anomaly", "percentile", "trend", "since 1990", "monsoon rain changed"])
                    is_alert = any(w in req.text.lower() for w in ["alert", "warning", "cyclone", "storm", "चेतावनी", "अलर्ट"])
                    is_risk = any(w in req.text.lower() for w in ["risk", "extreme event", "heatwave risk", "cold wave risk", "severe weather risk", "जोखिम", "खतरा"])
                    is_advisory = is_hazard_advisory or any(w in req.text.lower() for w in advisory_keywords)

                    if is_climate:
                        intent = "climate_history"
                    elif is_risk:
                        intent = "risk"
                    elif is_alert:
                        intent = "alert"
                    elif is_advisory:
                        intent = "advisory"
                    else:
                        intent = "forecast"
            except Exception as exc:
                logger.warning("intent_model_failed", extra={"error": str(exc)})
                confidence = None
                router_path = "deterministic"
                if is_hazard_advisory:
                    intent = "advisory"
        else:
            confidence = None
            router_path = "deterministic"
            if is_hazard_advisory:
                intent = "advisory"
            else:
                # Check intent keywords
                is_climate = any(w in req.text.lower() for w in ["climate", "normal", "anomaly", "percentile", "trend", "since 1990", "monsoon rain changed"])
                is_alert = any(w in req.text.lower() for w in ["alert", "warning", "cyclone", "storm", "चेतावनी", "अलर्ट"])
                is_risk = any(w in req.text.lower() for w in ["risk", "extreme event", "heatwave risk", "cold wave risk", "severe weather risk", "जोखिम", "खतरा"])
                is_advisory = any(w in req.text.lower() for w in advisory_keywords)

                if is_climate:
                    intent = "climate_history"
                elif is_risk:
                    intent = "risk"
                elif is_alert:
                    intent = "alert"
                elif is_advisory:
                    intent = "advisory"
                else:
                    intent = "forecast"

        if intent in ("climate", "climate_history"):
            intent = "climate_history"
            if is_model_enabled("climate"):
                models_invoked.append({"id": "climate_trend_v1", "version": "v1.0", "used": True})
            t0 = time.time()
            metric = "rain" if "rain" in req.text.lower() else "temperature"
            evidence_packets = await get_climate(place=place_ref, metric=metric, period="2026-05")
            tools_executed.append({
                "name": "get_climate",
                "args": {"place": place_ref.id, "metric": metric, "period": "2026-05"},
                "latency_ms": int((time.time() - t0) * 1000),
                "source": evidence_packets[0].source if evidence_packets else "era5",
                "provenance": evidence_packets[0].provenance if evidence_packets else "live",
            })
        elif intent in ("risk", "extreme_event"):
            intent = "risk"
            if is_model_enabled("extreme_event"):
                models_invoked.append({"id": "extreme_event_risk_v1", "version": "v1.0", "used": True})
            t0 = time.time()
            evidence_packets = await get_risk_outlook(place=place_ref, lead_day=1)
            tools_executed.append({
                "name": "get_risk_outlook",
                "args": {"place": place_ref.id, "lead_day": 1},
                "latency_ms": int((time.time() - t0) * 1000),
                "source": evidence_packets[0].source if evidence_packets else "extreme_event_risk",
                "provenance": evidence_packets[0].provenance if evidence_packets else "live",
            })
        elif intent == "alert":
            t0 = time.time()
            evidence_packets = await get_alerts(place=place_ref)
            tools_executed.append({
                "name": "get_alerts",
                "args": {"place": place_ref.id},
                "latency_ms": int((time.time() - t0) * 1000),
                "source": evidence_packets[0].source if evidence_packets else "sachet",
                "provenance": evidence_packets[0].provenance if evidence_packets else "live",
            })
        elif intent == "advisory":
            if is_model_enabled("rag"):
                models_invoked.append({"id": "rag_advisory_engine", "version": "v1.0", "used": True})
            t0 = time.time()
            evidence_packets = await search_knowledge(query=req.text, lang=lang)
            tools_executed.append({
                "name": "search_knowledge",
                "args": {"query": req.text, "lang": lang},
                "latency_ms": int((time.time() - t0) * 1000),
                "source": evidence_packets[0].source if evidence_packets else "ndma",
                "provenance": evidence_packets[0].provenance if evidence_packets else "documented-sample",
            })
        else:
            intent = "forecast"
            # Target day index: 0 = today, 1 = tomorrow
            tomorrow_kw = ["tomorrow", "कल", "उद्या", "আগামীকাল", "কাল", "రేపు", "நாளை", "ଆସନ୍ତାକାଲି", "କାଲି"]
            today_kw = ["today", "आज", "এখন", "ఈ రోజు", "నేడు", "இன்று", "ଆଜି"]
            day_target = 1  # Default tomorrow
            if any(k in req.text.lower() for k in today_kw):
                day_target = 0
            elif any(k in req.text.lower() for k in tomorrow_kw):
                day_target = 1

            t0 = time.time()
            req_ml_mode = getattr(req, "ml_mode", "raw")
            effective_ml_mode = req_ml_mode if (req_ml_mode == "ml" and is_model_enabled("bias_correction")) else "raw"
            evidence_packets = await get_forecast(
                place=place_ref,
                day=day_target,
                forecast_service=self.forecast_service,
                ml_mode=effective_ml_mode,
            )
            bias_corrected = any(p.id.endswith("-corrected") for p in evidence_packets)
            if bias_corrected and is_model_enabled("bias_correction"):
                models_invoked.append({"id": "NWP_BiasCorrection_v1", "version": "1.0.0", "used": True})

            tools_executed.append({
                "name": "get_forecast",
                "args": {"place": place_ref.id, "day": day_target, "ml_mode": effective_ml_mode},
                "latency_ms": int((time.time() - t0) * 1000),
                "source": evidence_packets[0].source if evidence_packets else "open_meteo",
                "provenance": evidence_packets[0].provenance if evidence_packets else "live",
            })

        # 7. Stream evidence packets
        for pkt in evidence_packets:
            yield {
                "event": "evidence",
                "data": pkt.model_dump(mode="json"),
            }

        # 8. Extract values from evidence for grounded answer formulation
        rain_val: float | None = None
        temp_val: float | None = None
        source_display = "Open-Meteo"
        issued_time_str = ""

        if evidence_packets:
            p0 = evidence_packets[0]
            source_display = p0.source
            if "open_meteo" in p0.source:
                source_display = "Open-Meteo"
            elif "sachet" in p0.source.lower():
                source_display = "NDMA SACHET"
            elif "era5" in p0.source.lower():
                source_display = "ERA5 via Open-Meteo"

            if p0.issued_at:
                issued_time_str = p0.issued_at.strftime("%H:%M UTC")

            day_packet = None
            for p in evidence_packets:
                if any(v.step == day_target for v in p.values if v.step is not None):
                    day_packet = p
                    break

            target_packets = [day_packet] if day_packet else evidence_packets
            for pkt in target_packets:
                for v in pkt.values:
                    if v.variable in ("rain_sum", "rain", "rain_mm", "precipitation_sum") and isinstance(v.value, (int, float)):
                        rain_val = float(v.value)
                    elif v.variable in ("tmax", "temperature", "temp_c", "temperature_2m_max") and isinstance(v.value, (int, float)):
                        temp_val = float(v.value)

        # 9. Compose answer via LLM with structured evidence
        prompt_evidence = [p.model_dump(mode="json") for p in evidence_packets]
        if intent == "advisory":
            sys_content = (
                "You are WeatherGPT, an official public-safety weather assistant for India.\n"
                "Compose advisory answers from the retrieved chunks with citations ([chunk_id, source, page] from chunk metadata only).\n"
                "Only state facts and safety rules present in the provided evidence packets.\n"
                "Never invent, assume, or hallucinate guidelines or place names.\n"
                f"Answer in language code '{lang}'. Name the source: {source_display}."
            )
        else:
            sys_content = (
                "You are WeatherGPT, a factual grounded weather assistant for India.\n"
                "Only state facts and numbers present in the provided evidence packets.\n"
                "Never invent, assume, or hallucinate a weather number.\n"
                f"Answer in language code '{lang}'. Name the source: {source_display}."
            )

        messages = [
            {
                "role": "system",
                "content": sys_content,
            },
            {
                "role": "user",
                "content": f"User Query: {req.text}\nPlace: {p_name}\nEvidence Packets: {prompt_evidence}",
            },
        ]

        llm_resp = await self.llm.complete(messages=messages, stream=False)
        answer_text = llm_resp.get("content", "") if isinstance(llm_resp, dict) else str(llm_resp or "")

        # 10. Grounding Verification
        v_result = verify_grounding(answer_text, evidence_packets)
        fallback_used = False

        if not v_result.is_grounded:
            logger.warning("grounding_verification_failed_regenerating", extra={"reasons": v_result.reasons})
            # Attempt 1 retry with strict reminder
            retry_messages = messages + [
                {"role": "assistant", "content": answer_text},
                {
                    "role": "user",
                    "content": f"Verification failed: {v_result.reasons}. Rewrite your answer using ONLY numbers from the evidence.",
                },
            ]
            llm_retry = await self.llm.complete(messages=retry_messages, stream=False)
            retry_text = llm_retry.get("content", "") if isinstance(llm_retry, dict) else str(llm_retry or "")
            v_retry = verify_grounding(retry_text, evidence_packets)

            if v_retry.is_grounded:
                answer_text = retry_text
                v_result = v_retry
            else:
                # Fall back to vetted deterministic template built directly from evidence
                fallback_used = True
                logger.warning("grounding_retry_failed_falling_back_to_template", extra={"reasons": v_retry.reasons})
                if intent == "advisory":
                    top_guidance = ""
                    top_chunk_id = ""
                    top_source = ""
                    top_page = ""
                    for p in evidence_packets:
                        for v in p.values:
                            if v.variable == "guidance" and not top_guidance:
                                top_guidance = str(v.value)
                            elif v.variable == "chunk_id" and not top_chunk_id:
                                top_chunk_id = str(v.value)
                            elif v.variable in ("doc_source", "source") and not top_source:
                                top_source = str(v.value)
                            elif v.variable == "page" and not top_page:
                                top_page = str(v.value)
                        if not top_source and p.source:
                            top_source = p.source

                    guidance_prefix = ""
                    if lang == "hi":
                        guidance_prefix = "आधिकारिक दिशानिर्देशों के अनुसार:\n"
                    elif lang == "bn":
                        guidance_prefix = "অফিসিয়াল নির্দেশিকা অনুসারে:\n"
                    elif lang == "mr":
                        guidance_prefix = "अधिकृत मार्गदर्शक तत्त्वांनुसार:\n"
                    elif lang == "te":
                        guidance_prefix = "అధికారిక మార్గదర్శకాల ప్రకారం:\n"
                    elif lang == "ta":
                        guidance_prefix = "அதிகாரப்பூர்வ வழிகாட்டுதல்களின்படி:\n"
                    elif lang == "or":
                        guidance_prefix = "ସରକାରୀ ନିର୍ଦ୍ଦେଶାବଳୀ ଅନୁଯାୟୀ:\n"

                    top_src_display = top_source or (evidence_packets[0].source if evidence_packets else "NDMA")
                    page_str = f", p. {top_page}" if top_page else ""

                    if top_chunk_id == "no_official_guidance":
                        answer_text = f"{guidance_prefix}{top_guidance}" if guidance_prefix else top_guidance
                    elif top_guidance:
                        clean_guidance = top_guidance.strip()
                        if clean_guidance.startswith("## "):
                            clean_guidance = clean_guidance.split("\n", 1)[-1].strip()
                        answer_text = f'{guidance_prefix}"{clean_guidance}" ({top_src_display}{page_str})'
                    else:
                        answer_text = f"{guidance_prefix}Official safety advisory is available." if guidance_prefix else "Official safety advisory is available."
                elif intent == "risk":
                    risk_lvl = "low"
                    for p in evidence_packets:
                        for v in p.values:
                            if v.variable == "risk_level":
                                risk_lvl = str(v.value)
                    if lang == "hi":
                        answer_text = f"{p_name} के लिए चरम मौसम जोखिम स्तर: {risk_lvl}। यह आधिकारिक चेतावनी नहीं है।"
                    else:
                        answer_text = f"Extreme weather risk outlook for {p_name}: {risk_lvl} risk. This is not an official warning."
                elif intent == "alert":
                    alert_text = ""
                    for p in evidence_packets:
                        for v in p.values:
                            if v.variable in ("headline", "alert", "warning", "description") and v.value:
                                alert_text = str(v.value)
                                break
                        if alert_text:
                            break
                    if alert_text:
                        answer_text = alert_text
                    elif lang == "hi":
                        answer_text = f"{p_name} के लिए कोई सक्रिय मौसम चेतावनी नहीं है।"
                    elif lang == "bn":
                        answer_text = f"{p_name}-এর জন্য কোনো সক্রিয় আবহাওয়া সতর্কতা নেই।"
                    elif lang == "mr":
                        answer_text = f"{p_name} साठी कोणताही सक्रिय हवामान इशारा नाही."
                    elif lang == "te":
                        answer_text = f"{p_name} కొరకు క్రియాశీల వాతావరణ హెచ్చరికలు లేవు."
                    elif lang == "ta":
                        answer_text = f"{p_name} க்கு செயலில் உள்ள வானிலை எச்சரிக்கைகள் எதுவும் இல்லை."
                    elif lang == "or":
                        answer_text = f"{p_name} ପାଇଁ କୌଣସି ସକ୍ରିୟ ପାଣିପାଗ ଚେତାବନୀ ନାହିଁ।"
                    else:
                        answer_text = f"No active weather warnings for {p_name}."
                elif rain_val is not None and temp_val is not None:
                    if lang == "hi":
                        rf_phrase = get_hindi_rainfall_phrase(rain_val)
                        answer_text = (
                            f"{source_display} पूर्वानुमान: {p_name} में कल {rf_phrase} ({rain_val:.1f} मिमी) "
                            f"और तापमान {temp_val:.1f} डिग्री रहेगा।"
                        )
                    elif lang == "mr":
                        answer_text = (
                            f"{source_display} हवामान अंदाजानुसार उद्या {p_name} मध्ये पाऊस {rain_val:.1f} मिमी आणि तापमान {temp_val:.1f} अंश सेल्सिअस राहण्याची शक्यता आहे।"
                        )
                    elif lang == "bn":
                        answer_text = (
                            f"{source_display} পূর্বাভাস অনুযায়ী আগামীকাল {p_name}-এ বৃষ্টিপাত {rain_val:.1f} মিমি এবং তাপমাত্রা {temp_val:.1f} ডিগ্রি সেলসিয়াস হতে পারে।"
                        )
                    elif lang == "te":
                        answer_text = (
                            f"{source_display} సూచన ప్రకారం రేపు {p_name} లో వర్షం {rain_val:.1f} మి.మీ మరియు ఉష్ణోగ్రత {temp_val:.1f} డిగ్రీల సెల్సియస్ ఉండే అవకాశం ఉంది."
                        )
                    elif lang == "ta":
                        answer_text = (
                            f"{source_display} வானிலை முன்னறிவிப்பின்படி நாளை {p_name} இல் மழை {rain_val:.1f} மிமீ மற்றும் வெப்பநிலை {temp_val:.1f} டிகிரி செல்சியஸ் பதிவாக வாய்ப்புள்ளது."
                        )
                    elif lang == "or":
                        answer_text = (
                            f"{source_display} ପୂର୍ବାନୁମାନ ଅନୁଯାୟୀ ଆସନ୍ତାକାଲି {p_name} ରେ ବର୍ଷା {rain_val:.1f} ମିମି ଏବଂ ତାପମାତ୍ରା {temp_val:.1f} ଡିଗ୍ରୀ ସେଲସିୟସ ରହିପାରେ।"
                        )
                    else:
                        answer_text = (
                            f"According to {source_display} forecast for {p_name}: tomorrow expects {rain_val:.1f} mm rain "
                            f"and a temperature of {temp_val:.1f} degC."
                        )
                elif p_name != req.text:
                    if lang == "hi":
                        answer_text = f"{source_display} के अनुसार {p_name} के लिए पूर्वानुमान उपलब्ध नहीं है।"
                    else:
                        answer_text = f"According to {source_display}, forecast data is currently unavailable for {p_name}."
                else:
                    if lang == "hi":
                        answer_text = f"{source_display} के अनुसार पूर्वानुमान उपलब्ध नहीं है।"
                    else:
                        answer_text = f"According to {source_display}, forecast data is currently unavailable."

        # Apply dynamic glossary replacements from admin service if configured
        try:
            from services.api.app.modules.admin.service import admin_service
            g_terms = admin_service.get_glossary(lang).get("terms", {})
            for term_key, term_val in g_terms.items():
                if term_key == "rain" and term_val and term_val != "बारिश" and "बारिश" in answer_text:
                    answer_text = answer_text.replace("बारिश", term_val)
        except Exception:
            pass

        # 11. Stream tokens
        for word in answer_text.split(" "):
            yield {
                "event": "token",
                "data": {"text": word + " "},
            }

        # 12. Build and Stream Card Event
        card_data: dict[str, Any] = {}
        if intent == "risk":
            card_headline = f"{p_name} Risk Outlook" if lang != "hi" else f"{p_name} चरम मौसम जोखिम"
            risk_prob_str = "Low"
            top_drivers_str = ""
            for p in evidence_packets:
                for v in p.values:
                    if v.variable == "risk_level":
                        risk_prob_str = str(v.value)
                    elif v.variable == "top_drivers":
                        top_drivers_str = str(v.value)
            card_data = {
                "headline": card_headline,
                "key_values": {
                    "Risk Level" if lang != "hi" else "जोखिम स्तर": risk_prob_str.title(),
                    "Top Drivers" if lang != "hi" else "मुख्य कारक": top_drivers_str or "Baseline climatology",
                },
                "source_line": "WeatherGPT Extreme-Event Risk Classifier (v1.0)",
                "caveat": "This is not an official warning. Official warnings are issued exclusively by IMD.",
                "actions": ["View Alerts", "Safety Guidelines"],
            }
        elif intent == "advisory":
            if p_name and p_name not in ("India", "भारत", "all_india", "in_national") and p_name != req.text:
                card_headline = f"{p_name} Advisory" if lang != "hi" else f"{p_name} मौसम व सुरक्षा सलाह"
            else:
                card_headline = ADVISORY_TITLES.get(lang, "Safety & Weather Advisory")
            first_val = evidence_packets[0].values[0].value if evidence_packets and evidence_packets[0].values else "Safety"
            card_data = {
                "headline": card_headline,
                "key_values": {
                    "Topic" if lang != "hi" else "विषय": str(first_val),
                    "Source" if lang != "hi" else "स्रोत": evidence_packets[0].source if evidence_packets else "Official Advisory",
                },
                "source_line": f"Source: {evidence_packets[0].source} ({evidence_packets[0].attribution})" if evidence_packets else "Official Safety Guidance",
                "caveat": "Official Safety & Agriculture Guidance",
                "actions": ["112 (Emergency)", "1077 (Disaster)", "1800-180-1551 (Kisan Call Centre)"],
            }
        else:
            card_headline = f"{p_name} Weather" if lang != "hi" else f"{p_name} का मौसम"
            key_values: dict[str, str] = {}
            if rain_val is not None:
                key_values["Rain" if lang != "hi" else "बारिश"] = f"{rain_val:.1f} mm" if lang != "hi" else f"{rain_val:.1f} मिमी"
            if temp_val is not None:
                key_values["Temperature" if lang != "hi" else "तापमान"] = f"{temp_val:.1f} degC" if lang != "hi" else f"{temp_val:.1f} डिग्री"

            source_line = f"Data: {source_display} (global model, CC BY 4.0)"
            if issued_time_str:
                source_line += f", issued {issued_time_str}"

            card_data = {
                "headline": card_headline,
                "key_values": key_values,
                "source_line": source_line,
                "caveat": "",
                "actions": ["View Hourly", "Set Alert"] if lang != "hi" else ["प्रति घंटा देखें", "अलर्ट सेट करें"],
            }
        yield {
            "event": "card",
            "data": card_data,
        }

        # 13. Stream Trace Event (Ticket R2.4, R8.4)
        checked_numbers = extract_numbers_from_text(answer_text)
        llm_metrics = getattr(self.llm, "last_call_metrics", None)
        if isinstance(llm_metrics, dict):
            llm_provider = llm_metrics.get("provider", "none")
            llm_model = llm_metrics.get("model", "none")
            tokens_in = llm_metrics.get("prompt_tokens", 0)
            tokens_out = llm_metrics.get("completion_tokens", 0)
        else:
            llm_provider = getattr(self.llm, "provider_name", "none")
            llm_model = getattr(self.llm, "model", "none")
            tokens_in = 0
            tokens_out = 0

        trace_payload = {
            "intent": intent,
            "confidence": confidence,
            "router_path": router_path,
            "tools": tools_executed,
            "models": models_invoked,
            "verifier": {
                "passed": v_result.is_grounded if not fallback_used else True,
                "checked_numbers": checked_numbers,
                "failures": v_result.reasons,
                "fallback_used": fallback_used,
            },
            "llm": {
                "provider": llm_provider,
                "model": llm_model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            },
        }
        yield {
            "event": "trace",
            "data": trace_payload,
        }

        # 14. Done Event
        latency_ms = int((time.time() - start_time) * 1000)
        yield {
            "event": "done",
            "data": {"latency_ms": latency_ms},
        }

    handle_chat_stream = run_chat

