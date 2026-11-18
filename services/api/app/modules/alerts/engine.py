from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Any

import yaml

from services.api.app.evidence.models import AlertModel

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[5]
TEMPLATES_PATH = ROOT / "seeds" / "i18n" / "alert-templates.yaml"

_TEMPLATES_CACHE: dict[str, Any] | None = None


def _load_templates() -> dict[str, Any]:
    global _TEMPLATES_CACHE
    if _TEMPLATES_CACHE is None:
        if TEMPLATES_PATH.exists():
            with TEMPLATES_PATH.open("r", encoding="utf-8") as f:
                _TEMPLATES_CACHE = yaml.safe_load(f) or {}
        else:
            _TEMPLATES_CACHE = {}
    return _TEMPLATES_CACHE


def _distance_point_to_segment(
    px: float, py: float, x1: float, y1: float, x2: float, y2: float
) -> float:
    """Distance from point (px, py) to line segment (x1, y1)-(x2, y2)."""
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5

    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5


def point_in_polygon(
    lat: float, lon: float, polygon: list[tuple[float, float]], tolerance: float = 1e-4
) -> bool:
    """Check if (lat, lon) is inside or on the boundary of polygon [(lat1, lon1), ...]."""
    if len(polygon) < 3:
        return False

    n = len(polygon)
    # Check boundary first (with tolerance for border cases)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if _distance_point_to_segment(lat, lon, x1, y1, x2, y2) <= tolerance:
            return True

    # Standard ray-casting algorithm
    inside = False
    j = n - 1
    for i in range(n):
        yi, xi = polygon[i]
        yj, xj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside


def parse_polygon_string(poly_text: str) -> list[tuple[float, float]]:
    """Parse space-separated 'lat,lon' pairs from CAP XML polygon."""
    coords: list[tuple[float, float]] = []
    if not poly_text or not poly_text.strip():
        return coords
    for pair in poly_text.strip().split():
        parts = pair.split(",")
        if len(parts) >= 2:
            try:
                coords.append((float(parts[0]), float(parts[1])))
            except ValueError:
                pass
    return coords


def render_alert_template(alert: AlertModel, place_name: str, lang: str = "en") -> dict[str, str]:
    """Render vetted alert wording from seeds/i18n/alert-templates.yaml."""
    templates = _load_templates()
    lang_tmpl = templates.get(lang, templates.get("en", {}))

    meaning_map = lang_tmpl.get("meaning", {})
    meaning = meaning_map.get(alert.level, "")

    valid_from_str = alert.onset.strftime("%H:%M IST") if hasattr(alert.onset, "strftime") else str(alert.onset)
    valid_to_str = alert.expires.strftime("%H:%M IST") if hasattr(alert.expires, "strftime") else str(alert.expires)
    issued_at_str = alert.sent.strftime("%H:%M IST") if hasattr(alert.sent, "strftime") else str(alert.sent)

    headline = lang_tmpl.get("headline", "{level_color} alert: {hazard} in {place}").format(
        level_color=alert.level,
        hazard=alert.hazard,
        place=place_name,
    )

    body = lang_tmpl.get(
        "body",
        "{sender} has issued a {level_color} alert for {hazard} in {place}, valid from {valid_from} to {valid_to}."
    ).format(
        sender=alert.sender,
        level_color=alert.level,
        hazard=alert.hazard,
        place=place_name,
        valid_from=valid_from_str,
        valid_to=valid_to_str,
    )

    source_line = lang_tmpl.get(
        "source_line",
        "Official alert from {sender}, relayed via {channel}. Issued {issued_at}."
    ).format(
        sender=alert.sender,
        channel="SACHET",
        issued_at=issued_at_str,
    )

    return {
        "headline": headline,
        "body": body,
        "meaning": meaning,
        "source_line": source_line,
        "advice_header": lang_tmpl.get("advice_header", "What officials advise"),
        "advice_fallback": lang_tmpl.get("advice_fallback", "Follow instructions from your local authorities."),
    }


class AlertEngine:
    def __init__(self) -> None:
        self._alerts: dict[str, AlertModel] = {}
        self._references_map: dict[str, str] = {}

    def get_all_active(self) -> list[AlertModel]:
        now = dt.datetime.now(dt.timezone.utc)
        return [a for a in self._alerts.values() if a.expires > now]

    async def get_active_alerts(self, place_id: str | None = None) -> list[AlertModel]:
        now = dt.datetime.now(dt.timezone.utc)
        active = [a for a in self._alerts.values() if a.expires > now]
        if place_id:
            # Filter by place if applicable
            return [
                a
                for a in active
                if any(
                    place_id.lower() in (area.get("areaDesc") or area.get("area_desc") or "").lower()
                    for area in a.areas
                )
            ]
        return active

    def ingest_sample_alert(self, alert: AlertModel, references: str | None = None) -> None:
        # Ignore Test and Exercise statuses
        if alert.status in ("Test", "Exercise", "Draft"):
            logger.info("Alert %s ignored in production (status: %s)", alert.id, alert.status)
            return

        ref_id = references
        # Handle Cancel
        if alert.msg_type == "Cancel":
            if ref_id and ref_id in self._alerts:
                del self._alerts[ref_id]
            if alert.id in self._alerts:
                del self._alerts[alert.id]
            return

        # Handle Update
        if alert.msg_type == "Update" and ref_id and ref_id in self._alerts:
            del self._alerts[ref_id]

        self._alerts[alert.id] = alert
        if ref_id:
            self._references_map[alert.id] = ref_id

    def match_alerts(
        self, lat: float, lon: float, district: str | None = None
    ) -> list[AlertModel]:
        now = dt.datetime.now(dt.timezone.utc)
        matched = []

        for alert in self._alerts.values():
            if alert.expires <= now:
                continue

            hit = False
            for area in alert.areas:
                poly_str = area.get("polygon", "")
                if poly_str:
                    coords = parse_polygon_string(poly_str)
                    if coords and point_in_polygon(lat, lon, coords):
                        hit = True
                        break

                # District fallback
                area_desc = area.get("areaDesc") or area.get("area_desc")
                if district and area_desc:
                    desc = area_desc.lower()
                    d_lower = district.lower()
                    if d_lower in desc or desc in d_lower:
                        hit = True
                        break

            if hit:
                matched.append(alert)

        return matched
