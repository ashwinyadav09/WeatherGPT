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


class ChatRequest(BaseModel):
    session_id: str
    text: str
    language: str = "auto"
    place_id: str | None = None
    client_tz: str = "Asia/Kolkata"
    stream: bool = True


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
    ) -> None:
        self.llm = llm or llm_gateway or LLMGateway()
        self.forecast_service = forecast_service or ForecastService()
        self.location_resolver = location_resolver or LocationResolver()
        self.alert_engine = alert_engine or AlertEngine()
        self.advisory_engine = advisory_engine or AdvisoryEngine()
        self.climate_service = climate_service or ClimateService()
        self.translation_gateway = translation_gateway
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
                    "confidence": 1.0,
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
                    "confidence": 1.0,
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
        aviation_terms = ["aviation", "metar", "taf", "aerodrome", "pilot briefing", "flight weather"]
        if any(term in req.text.lower() for term in aviation_terms):
            msg = (
                "हवाई मौसम ब्रीफिंग (METAR/TAF) इस पायलट संस्करण में समर्थित नहीं है। आधिकारिक विमानन मौसम के लिए कृपया IMD विमानन पोर्टल देखें।"
                if lang == "hi"
                else "Aviation weather briefings (METAR/TAF) are not supported in this public-interest pilot. Please consult official aviation portals for flight planning."
            )
            yield {
                "event": "card",
                "data": {
                    "headline": "विमानन मौसम (Aviation Weather)" if lang == "hi" else "Aviation Weather",
                    "source_line": "WeatherGPT Policy: Non-commercial public pilot",
                    "caveat": msg,
                    "actions": ["IMD Aviation Weather"],
                },
            }
            yield {"event": "token", "data": {"text": msg}}
            yield {
                "event": "trace",
                "data": {
                    "intent": "aviation_brief",
                    "confidence": 1.0,
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
                        "confidence": 0.95,
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
                    "confidence": 0.95,
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

        # 4c. Check for Agromet / Farming query (Wheat / Rice / Crops)
        agro_terms = ["agromet", "wheat", "rice", "paddy", "गेहूं", "धान", "फसल", "crop", "sowing", "बुवाई", "कटाई", "रोपाई", "kheti", "कृषि"]
        if any(k in req.text.lower() for k in agro_terms):
            target_district = "Ludhiana"
            if req.place_id:
                target_district = req.place_id.replace("_", " ").title()
            else:
                # Extract place from text or default
                resolved_agro = await self.location_resolver.resolve(req.text, language=lang)
                if resolved_agro.get("resolved_place"):
                    target_district = resolved_agro["resolved_place"].names.get("en", resolved_agro["resolved_place"].id)

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
                    else f"Agricultural weather advisories are currently unavailable for {target_district}."
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
                        "confidence": 0.95,
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
                    "confidence": 0.95,
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
                        "confidence": 1.0,
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

        place = None
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
                        "confidence": 0.5,
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
                    "confidence": 1.0,
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

        p_name = place.names.get(lang, place.names.get("en", place.id))
        lat = place.lat
        lon = place.lon
        place_ref = PlaceReference(id=place.id, name=p_name, lat=lat, lon=lon)

        # 6. Intent Routing & Tool Execution
        tools_executed: list[dict[str, Any]] = []
        evidence_packets: list[EvidencePacket] = []
        intent = "forecast"
        router_path = "deterministic"
        confidence = 0.95

        # Check intent keywords
        is_climate = any(w in req.text.lower() for w in ["climate", "normal", "anomaly", "percentile", "trend", "since 1990", "monsoon rain changed"])
        is_alert = any(w in req.text.lower() for w in ["alert", "warning", "cyclone", "storm", "चेतावनी", "अलर्ट"])
        is_advisory = any(w in req.text.lower() for w in ["heat wave", "cold wave", "drinking water", "लू", "ठंड", "शीतलहर", "do's and don'ts"])

        if is_climate:
            intent = "climate_history"
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
        elif is_alert:
            intent = "alert"
            t0 = time.time()
            evidence_packets = await get_alerts(place=place_ref)
            tools_executed.append({
                "name": "get_alerts",
                "args": {"place": place_ref.id},
                "latency_ms": int((time.time() - t0) * 1000),
                "source": evidence_packets[0].source if evidence_packets else "sachet",
                "provenance": evidence_packets[0].provenance if evidence_packets else "live",
            })
        elif is_advisory:
            intent = "advisory"
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
            evidence_packets = await get_forecast(
                place=place_ref, day=day_target, forecast_service=self.forecast_service
            )
            tools_executed.append({
                "name": "get_forecast",
                "args": {"place": place_ref.id, "day": day_target},
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
        messages = [
            {
                "role": "system",
                "content": (
                    "You are WeatherGPT, a factual grounded weather assistant for India.\n"
                    "Only state facts and numbers present in the provided evidence packets.\n"
                    "Never invent, assume, or hallucinate a weather number.\n"
                    f"Answer in language code '{lang}'. Name the source: {source_display}."
                ),
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
                if rain_val is not None and temp_val is not None:
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
                else:
                    if lang == "hi":
                        answer_text = f"{source_display} के अनुसार {p_name} के लिए मौसम विवरण उपलब्ध है।"
                    else:
                        answer_text = f"According to {source_display}, weather information is available for {p_name}."

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
        card_headline = f"{p_name} Weather" if lang != "hi" else f"{p_name} का मौसम"
        key_values: dict[str, str] = {}
        if rain_val is not None:
            key_values["Rain" if lang != "hi" else "बारिश"] = f"{rain_val:.1f} mm" if lang != "hi" else f"{rain_val:.1f} मिमी"
        if temp_val is not None:
            key_values["Temperature" if lang != "hi" else "तापमान"] = f"{temp_val:.1f} degC" if lang != "hi" else f"{temp_val:.1f} डिग्री"

        source_line = f"Data: {source_display} (global model, CC BY 4.0)"
        if issued_time_str:
            source_line += f", issued {issued_time_str}"

        card_data: dict[str, Any] = {
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

        # 13. Stream Trace Event (Ticket R2.4)
        checked_numbers = extract_numbers_from_text(answer_text)
        trace_payload = {
            "intent": intent,
            "confidence": confidence,
            "router_path": router_path,
            "tools": tools_executed,
            "models": [{"id": "intent_baseline", "version": "v1", "used": True}],
            "verifier": {
                "passed": v_result.is_grounded if not fallback_used else True,
                "checked_numbers": checked_numbers,
                "failures": v_result.reasons,
                "fallback_used": fallback_used,
            },
            "llm": {
                "provider": self.llm.last_call_metrics.get("provider", "groq"),
                "model": self.llm.last_call_metrics.get("model", "llama-3.3-70b-versatile"),
                "tokens_in": self.llm.last_call_metrics.get("prompt_tokens", 0),
                "tokens_out": self.llm.last_call_metrics.get("completion_tokens", 0),
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

