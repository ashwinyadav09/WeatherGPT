"""Agent Tools for WeatherGPT (Ticket R2.1).

Defines tool functions for the conversational agent:
- geocode(text, language, hint)
- get_forecast(place, day, range_days)
- get_alerts(place)
- get_climate(place, metric, period, statistic)
- get_risk_outlook(place)
- search_knowledge(query, lang)

All tools:
- Return list[EvidencePacket] with source, provenance, issued/valid times, units, attribution.
- Never raise raw provider errors to caller/LLM (errors are wrapped in evidence packets).
- Export TOOL_SCHEMAS for OpenAI-compatible function calling.
- Provide call_tool(name, args) dispatcher.
"""
from __future__ import annotations

import datetime as dt
import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Coroutine

from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem
from services.api.app.modules.alerts.engine import AlertEngine
from services.api.app.modules.climate.service import ClimateService
from services.api.app.modules.forecast.service import ForecastService
from services.api.app.modules.location.data import PLACES_BY_ID
from services.api.app.modules.location.resolver import LocationResolver

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[5]
GUIDANCE_DIR = ROOT / "seeds" / "guidance"


# ============================================================================
# Helper Functions
# ============================================================================

def _make_error_packet(
    tool_name: str,
    error_msg: str,
    place_ref: PlaceReference | None = None,
) -> EvidencePacket:
    """Creates a structured error EvidencePacket so tools never raise raw exceptions."""
    now = dt.datetime.now(dt.timezone.utc)
    ref = place_ref or PlaceReference(id="unknown", name="Unknown", lat=0.0, lon=0.0)
    return EvidencePacket(
        id=f"err_{uuid.uuid4().hex[:12]}",
        source=f"agent.tool.{tool_name}",
        authority_tier=5,
        provenance="live",
        issued_at=now,
        valid_from=now,
        valid_to=now + dt.timedelta(hours=1),
        place=ref,
        values=[
            ValueItem(variable="status", value="error", unit="text"),
            ValueItem(variable="error", value=error_msg, unit="text"),
        ],
        attribution="WeatherGPT Agent System",
        fetched_at=now,
    )


async def _resolve_place_reference(
    place: str | PlaceReference | dict[str, Any],
    resolver: LocationResolver | None = None,
) -> PlaceReference:
    """Resolves arbitrary place input to a standard PlaceReference."""
    if isinstance(place, PlaceReference):
        return place
    if isinstance(place, dict):
        return PlaceReference(
            id=str(place.get("id", "custom")),
            name=str(place.get("name", "Unknown")),
            lat=float(place.get("lat", 0.0)),
            lon=float(place.get("lon", 0.0)),
        )

    clean_str = str(place).strip()
    norm_key = clean_str.lower().replace(" ", "_")
    if norm_key in PLACES_BY_ID:
        p = PLACES_BY_ID[norm_key]
        return PlaceReference(
            id=p.id,
            name=p.names.get("en", p.id),
            lat=p.lat,
            lon=p.lon,
        )

    res = resolver or LocationResolver()
    resolved = await res.resolve(clean_str)
    if resolved.get("places"):
        first = resolved["places"][0]
        return PlaceReference(
            id=first.id,
            name=first.names.get("en", first.id),
            lat=first.lat,
            lon=first.lon,
        )

    return PlaceReference(id=norm_key, name=clean_str, lat=0.0, lon=0.0)


# ============================================================================
# Tool Implementations
# ============================================================================

async def geocode(
    text: str,
    language: str = "en",
    hint: str | None = None,
    resolver: LocationResolver | None = None,
) -> list[EvidencePacket]:
    """Turn a place name, in any supported language or script, into place records."""
    try:
        loc_res = resolver or LocationResolver()
        resolved = await loc_res.resolve(text, language=language, hint=hint)
        places = resolved.get("places", [])

        if not places:
            now = dt.datetime.now(dt.timezone.utc)
            return [
                EvidencePacket(
                    id=f"geo_none_{uuid.uuid4().hex[:10]}",
                    source="geocoding.resolver",
                    authority_tier=5,
                    provenance="live",
                    issued_at=now,
                    valid_from=now,
                    valid_to=now + dt.timedelta(hours=24),
                    place=PlaceReference(id="unknown", name=text, lat=0.0, lon=0.0),
                    values=[
                        ValueItem(variable="status", value="not_found", unit="text"),
                        ValueItem(variable="query", value=text, unit="text"),
                    ],
                    attribution="Open-Meteo Geocoding / GeoNames / OpenStreetMap",
                    fetched_at=now,
                )
            ]

        packets: list[EvidencePacket] = []
        now = dt.datetime.now(dt.timezone.utc)
        for p in places:
            p_name = p.names.get(language, p.names.get("en", p.id))
            place_ref = PlaceReference(id=p.id, name=p_name, lat=p.lat, lon=p.lon)
            values = [
                ValueItem(variable="place_id", value=p.id, unit="text"),
                ValueItem(variable="name", value=p_name, unit="text"),
                ValueItem(variable="lat", value=p.lat, unit="deg"),
                ValueItem(variable="lon", value=p.lon, unit="deg"),
                ValueItem(variable="state", value=p.state or "", unit="text"),
                ValueItem(variable="district", value=p.district or "", unit="text"),
            ]
            packets.append(
                EvidencePacket(
                    id=f"geo_{p.id}_{uuid.uuid4().hex[:8]}",
                    source="geocoding.resolver",
                    authority_tier=4,
                    provenance="live",
                    issued_at=now,
                    valid_from=now,
                    valid_to=now + dt.timedelta(hours=24),
                    place=place_ref,
                    values=values,
                    attribution="Open-Meteo Geocoding / GeoNames / OpenStreetMap",
                    fetched_at=now,
                )
            )
        return packets
    except Exception as exc:
        logger.warning("geocode_tool_failed", extra={"query": text, "error": str(exc)})
        return [_make_error_packet("geocode", str(exc))]


async def get_forecast(
    place: str | PlaceReference | dict[str, Any],
    day: int | str | None = 0,
    range_days: int | None = None,
    forecast_service: ForecastService | None = None,
    ml_mode: str = "raw",
) -> list[EvidencePacket]:
    """Forecast values for a place and day/range from the best available sources."""
    try:
        place_ref = await _resolve_place_reference(place)
        if place_ref.lat == 0.0 and place_ref.lon == 0.0:
            return [
                EvidencePacket(
                    id=f"fc_unresolved_{uuid.uuid4().hex[:8]}",
                    source="forecast.provider",
                    authority_tier=5,
                    provenance="live",
                    issued_at=dt.datetime.now(dt.timezone.utc),
                    valid_from=dt.datetime.now(dt.timezone.utc),
                    valid_to=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1),
                    place=place_ref,
                    values=[
                        ValueItem(variable="status", value="unavailable", unit="text"),
                        ValueItem(variable="reason", value="unresolved_coordinates", unit="text"),
                    ],
                    attribution="Forecast Provider",
                )
            ]

        svc = forecast_service or ForecastService()
        all_packets = await svc.get_forecast(
            place_id=place_ref.id,
            lat=place_ref.lat,
            lon=place_ref.lon,
            place_name=place_ref.name,
            ml_mode=ml_mode,
            elevation=getattr(place_ref, "elevation", 0.0) or 0.0,
        )

        # Parse target day index if given as string
        target_day: int | None = None
        if isinstance(day, int):
            target_day = day
        elif isinstance(day, str):
            day_clean = day.strip().lower()
            if day_clean in ["today", "आज", "0"]:
                target_day = 0
            elif day_clean in ["tomorrow", "कल", "उद्या", "কাল", "రేపు", "நாளை", "ଆସନ୍ତାକାଲି", "1"]:
                target_day = 1
            else:
                try:
                    target_day = int(day_clean)
                except ValueError:
                    # Try matching by ISO date string
                    filtered_date_pkts = [
                        p for p in all_packets if p.valid_from.date().isoformat() == day_clean
                    ]
                    if filtered_date_pkts:
                        return filtered_date_pkts

        # Filter by day or range
        if target_day is not None:
            # Daily packet with step == target_day
            matched_daily = [
                p
                for p in all_packets
                if any(v.step == target_day for v in p.values if v.step is not None)
            ]
            if matched_daily:
                # If target is today (day 0), also include current conditions packet if present
                if target_day == 0:
                    curr_pkts = [
                        p for p in all_packets if all(v.step is None for v in p.values)
                    ]
                    return curr_pkts + matched_daily
                return matched_daily

        if range_days is not None and range_days > 0:
            matched_range = [
                p
                for p in all_packets
                if any(
                    isinstance(v.step, int) and v.step < range_days
                    for v in p.values
                )
            ]
            if matched_range:
                return matched_range

        return all_packets
    except Exception as exc:
        logger.warning("get_forecast_tool_failed", extra={"place": str(place), "error": str(exc)})
        ref = place_ref if 'place_ref' in locals() and place_ref else (place if isinstance(place, PlaceReference) else None)
        return [_make_error_packet("get_forecast", str(exc), place_ref=ref)]


async def get_alerts(
    place: str | PlaceReference | dict[str, Any],
    alert_engine: AlertEngine | None = None,
) -> list[EvidencePacket]:
    """Active official alerts that cover a place."""
    try:
        place_ref = await _resolve_place_reference(place)
        engine = alert_engine or AlertEngine()

        matched_alerts = []
        if place_ref.lat != 0.0 or place_ref.lon != 0.0:
            matched_alerts = engine.match_alerts(lat=place_ref.lat, lon=place_ref.lon)
        if not matched_alerts:
            matched_alerts = await engine.get_active_alerts(place_id=place_ref.id)

        now = dt.datetime.now(dt.timezone.utc)
        if matched_alerts:
            packets: list[EvidencePacket] = []
            for alert in matched_alerts:
                values = [
                    ValueItem(variable="hazard", value=alert.hazard, unit="text"),
                    ValueItem(variable="severity", value=alert.severity, unit="text"),
                    ValueItem(variable="level", value=alert.level, unit="text"),
                    ValueItem(
                        variable="headline",
                        value=alert.text_by_language.get("en", alert.hazard),
                        unit="text",
                    ),
                ]
                packets.append(
                    EvidencePacket(
                        id=f"alt_{alert.id}_{uuid.uuid4().hex[:6]}",
                        source=alert.sender or "NDMA SACHET",
                        authority_tier=1,
                        provenance="live",
                        issued_at=alert.sent,
                        valid_from=alert.onset,
                        valid_to=alert.expires,
                        place=place_ref,
                        values=values,
                        attribution="NDMA SACHET (sachet.ndma.gov.in)",
                        fetched_at=now,
                    )
                )
            return packets

        # Clean no-active-warnings evidence packet
        return [
            EvidencePacket(
                id=f"alt_none_{uuid.uuid4().hex[:8]}",
                source="NDMA SACHET",
                authority_tier=1,
                provenance="live",
                issued_at=now,
                valid_from=now,
                valid_to=now + dt.timedelta(hours=24),
                place=place_ref,
                values=[
                    ValueItem(variable="active_alerts_count", value=0, unit="count"),
                    ValueItem(variable="status", value="no_active_warnings", unit="text"),
                ],
                attribution="NDMA SACHET (sachet.ndma.gov.in)",
                fetched_at=now,
            )
        ]
    except Exception as exc:
        logger.warning("get_alerts_tool_failed", extra={"place": str(place), "error": str(exc)})
        ref = place if isinstance(place, PlaceReference) else None
        return [_make_error_packet("get_alerts", str(exc), place_ref=ref)]


async def get_climate(
    place: str | PlaceReference | dict[str, Any],
    metric: str = "rain",
    period: str | None = None,
    statistic: str = "normal",
    threshold: float | None = None,
    climate_service: ClimateService | None = None,
) -> list[EvidencePacket]:
    """A climate statistic for a place and period against a stated baseline."""
    try:
        place_ref = await _resolve_place_reference(place)
        svc = climate_service or ClimateService()
        stat_res = await svc.get_stat(
            place_id=place_ref.id,
            variable=metric,
            period=period,
            statistic=statistic,
            threshold=threshold,
        )

        now = dt.datetime.now(dt.timezone.utc)
        unit = "mm" if "rain" in metric.lower() else "degC"
        values = [
            ValueItem(variable=f"{metric}_{statistic}", value=stat_res.get("value"), unit=unit),
            ValueItem(variable="normal", value=stat_res.get("normal"), unit=unit),
            ValueItem(variable="anomaly", value=stat_res.get("anomaly"), unit=unit),
            ValueItem(variable="percentile", value=stat_res.get("percentile"), unit="%"),
        ]
        if "rate_per_decade" in stat_res:
            values.append(ValueItem(variable="rate_per_decade", value=stat_res.get("rate_per_decade"), unit=f"{unit}/decade"))
        if "p_value" in stat_res:
            values.append(ValueItem(variable="p_value", value=stat_res.get("p_value"), unit="p"))
        if "n_years" in stat_res:
            values.append(ValueItem(variable="n_years", value=stat_res.get("n_years"), unit="years"))

        return [
            EvidencePacket(
                id=f"clim_{uuid.uuid4().hex[:10]}",
                source="ERA5 via Open-Meteo",
                authority_tier=3,
                provenance="live",
                issued_at=now,
                valid_from=now,
                valid_to=now + dt.timedelta(days=30),
                place=place_ref,
                values=values,
                attribution="ECMWF ERA5 via Open-Meteo (CC BY 4.0)",
                fetched_at=now,
            )
        ]
    except Exception as exc:
        logger.warning("get_climate_tool_failed", extra={"place": str(place), "error": str(exc)})
        ref = place if isinstance(place, PlaceReference) else None
        return [_make_error_packet("get_climate", str(exc), place_ref=ref)]


async def get_risk_outlook(
    place: str | PlaceReference | dict[str, Any],
    lead_day: int = 1,
) -> list[EvidencePacket]:
    """Extreme-event risk probabilities and SHAP drivers for severe weather hazards."""
    try:
        place_ref = await _resolve_place_reference(place)
        now = dt.datetime.now(dt.timezone.utc)

        from ml.extreme_event.service import ExtremeEventRiskService
        svc = ExtremeEventRiskService()

        # Try to obtain forecast tmax for the target place and lead day
        fc_tmax: float | None = None
        try:
            fc_svc = ForecastService()
            fc_pkts = await fc_svc.get_forecast(place_ref.id, place_ref.lat, place_ref.lon, place_ref.name)
            for p in fc_pkts:
                for v in p.values:
                    if v.variable in ("temperature_max", "tmax", "temperature_2m_max") and (v.step == lead_day or v.step is None):
                        if v.value is not None:
                            try:
                                fc_tmax = float(v.value)
                            except (ValueError, TypeError):
                                pass
                        break
                if fc_tmax is not None:
                    break
        except Exception:
            fc_tmax = None

        pred = svc.predict_risk(
            lat=place_ref.lat,
            lon=place_ref.lon,
            elev=float(getattr(place_ref, "elevation", 100.0) or 100.0),
            lead_day=lead_day,
            forecast_tmax=fc_tmax,
        )

        drivers_str = "; ".join(pred["top_drivers"]) if pred["top_drivers"] else "None identified"

        values = [
            ValueItem(variable="heat_wave_risk", value=pred["heat_wave_risk"], unit="probability"),
            ValueItem(variable="risk_level", value=pred["risk_level"], unit="text"),
            ValueItem(variable="top_drivers", value=drivers_str, unit="text"),
            ValueItem(variable="heavy_rain_risk", value="unavailable", unit="text"),
            ValueItem(
                variable="heavy_rain_exclusion_reason",
                value=pred["excluded_hazards"]["heavy_rain"]["reason"],
                unit="text",
            ),
            ValueItem(variable="cold_wave_risk", value="unavailable", unit="text"),
            ValueItem(
                variable="cold_wave_exclusion_reason",
                value=pred["excluded_hazards"]["cold_wave"]["reason"],
                unit="text",
            ),
            ValueItem(
                variable="advisory_note",
                value=pred["advisory_note"],
                unit="text",
            ),
        ]
        return [
            EvidencePacket(
                id=f"risk_{uuid.uuid4().hex[:10]}",
                source="WeatherGPT Extreme Event Model (Stage 2 Calibrated LightGBM)",
                authority_tier=4,
                provenance="live",
                issued_at=now,
                valid_from=now,
                valid_to=now + dt.timedelta(hours=48),
                place=place_ref,
                values=values,
                attribution=pred["attribution"],
                fetched_at=now,
            )
        ]
    except Exception as exc:
        logger.warning("get_risk_outlook_tool_failed", extra={"place": str(place), "error": str(exc)})
        ref = place if isinstance(place, PlaceReference) else None
        return [_make_error_packet("get_risk_outlook", str(exc), place_ref=ref)]


async def search_knowledge(
    query: str,
    lang: str = "en",
) -> list[EvidencePacket]:
    """Search vetted safety advisories, NDMA guidelines, and weather definitions."""
    try:
        from services.api.app.modules.advisory.rag import RagEngine

        rag = RagEngine.get_instance()
        dict_packets = rag.search_as_evidence(query=query, lang=lang)

        packets: list[EvidencePacket] = []
        for dp in dict_packets:
            pl_data = dp["place"]
            pl_ref = PlaceReference(
                id=pl_data.get("id", "all_india"),
                name=pl_data.get("name", "India"),
                lat=pl_data.get("lat", 20.5937),
                lon=pl_data.get("lon", 78.9629),
            )
            val_items = [
                ValueItem(variable=v["variable"], value=v["value"], unit=v.get("unit", "text"))
                for v in dp["values"]
            ]
            pkt = EvidencePacket(
                id=dp["id"],
                source=dp["source"],
                authority_tier=dp["authority_tier"],
                provenance=dp["provenance"],
                issued_at=dp["issued_at"],
                valid_from=dp["valid_from"],
                valid_to=dp["valid_to"],
                place=pl_ref,
                values=val_items,
                attribution=dp["attribution"],
                fetched_at=dp["fetched_at"],
            )
            packets.append(pkt)

        return packets
    except Exception as exc:
        logger.warning("search_knowledge_tool_failed", extra={"query": query, "error": str(exc)})
        return [_make_error_packet("search_knowledge", str(exc))]
    except Exception as exc:
        logger.warning("search_knowledge_tool_failed", extra={"query": query, "error": str(exc)})
        return [_make_error_packet("search_knowledge", str(exc))]


# ============================================================================
# Tool Schemas for LLM Tool Calling (OpenAI Compatible)
# ============================================================================

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "geocode",
            "description": "Turn a place name, in any supported language or script, into place records. Call this first whenever the user names a place.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The place name as the user wrote or spoke it."},
                    "language": {"type": "string", "description": "Language code (e.g. en, hi). Defaults to en."},
                    "hint": {"type": "string", "description": "Optional state or district to narrow the search."},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Forecast values (temperature, rain, etc.) for a place and time window from the best available sources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {"type": "string", "description": "Place name or place ID."},
                    "day": {
                        "type": ["integer", "string"],
                        "description": "Day index (0=today, 1=tomorrow) or string ('today', 'tomorrow', 'YYYY-MM-DD').",
                    },
                    "range_days": {"type": "integer", "description": "Number of forecast days to retrieve (1-7)."},
                    "ml_mode": {"type": "string", "enum": ["raw", "ml"], "description": "Whether to apply machine learning bias correction (ml) or raw NWP forecast (raw)."},
                },
                "required": ["place"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_alerts",
            "description": "Active official weather alerts that cover a place from NDMA SACHET.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {"type": "string", "description": "Place name or place ID to check alerts for."},
                },
                "required": ["place"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_climate",
            "description": "Historical climate statistic (normal, anomaly, percentile) for a place and period against a stated baseline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {"type": "string", "description": "Place name or place ID."},
                    "metric": {"type": "string", "enum": ["rain", "temperature"], "description": "Climate variable."},
                    "period": {"type": "string", "description": "Period e.g. '2026-05'."},
                    "statistic": {"type": "string", "enum": ["normal", "anomaly", "percentile", "days_above_threshold", "trend"], "description": "Statistic type."},
                },
                "required": ["place"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_outlook",
            "description": "Extreme-event risk outlook (heatwave, heavy rain, cold wave probabilities) for a place.",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {"type": "string", "description": "Place name or place ID."},
                },
                "required": ["place"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search vetted official safety advisories, NDMA guidelines, and weather definitions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query or hazard topic."},
                    "lang": {"type": "string", "description": "Language code (e.g. en, hi)."},
                },
                "required": ["query"],
            },
        },
    },
]


_TOOL_MAP: dict[str, Callable[..., Coroutine[Any, Any, list[EvidencePacket]]]] = {
    "geocode": geocode,
    "get_forecast": get_forecast,
    "get_alerts": get_alerts,
    "get_climate": get_climate,
    "get_risk_outlook": get_risk_outlook,
    "search_knowledge": search_knowledge,
}


async def call_tool(name: str, args: dict[str, Any]) -> list[EvidencePacket]:
    """Execute a tool by name with arguments dict. Returns list of EvidencePackets, never raises."""
    tool_fn = _TOOL_MAP.get(name)
    if not tool_fn:
        return [_make_error_packet("dispatcher", f"Unknown tool name: {name}")]

    try:
        return await tool_fn(**args)
    except Exception as exc:
        logger.warning("call_tool_failed", extra={"name": name, "args": args, "error": str(exc)})
        return [_make_error_packet(name, str(exc))]
