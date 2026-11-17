"""SACHET CAP alert ingest adapter for WeatherGPT.

Fetches the NDMA SACHET RSS feed, retrieves individual CAP 1.2 XML files,
and normalises them to the AlertModel schema. No LLM is in this path.

Allowlisted domains: sachet.ndma.gov.in only.
CAP polygon: lat,lon pairs → converted to GeoJSON [lon, lat] order.
Test and Exercise statuses: ignored and logged.
Update / Cancel: preserved as-is in msg_type for downstream deduplication.
"""
from __future__ import annotations

import logging
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

ALLOWLISTED_DOMAINS = {
    "sachet.ndma.gov.in",
}

IGNORED_STATUSES = {"Test", "Exercise", "Draft"}

SEVERITY_LEVEL_MAP: dict[str, str] = {
    "Extreme": "red",
    "Severe": "orange",
    "Moderate": "yellow",
    "Minor": "green",
    "Unknown": "yellow",
}


def severity_to_level(severity: str) -> str:
    """Map CAP severity to WeatherGPT alert level.

    Both keys are tested individually in test_sachet_adapter.py.
    """
    return SEVERITY_LEVEL_MAP.get(severity, "yellow")


def _strip_ns(tag: str) -> str:
    """Strip XML namespace from a tag name."""
    return tag.split("}", 1)[1] if "}" in tag else tag


def _iso(ts: str | None, fallback: str) -> str:
    """Return ts if it looks like an ISO datetime, else fallback."""
    if not ts:
        return fallback
    # Accept ISO with offset (+05:30) or Z; normalise to UTC
    ts = ts.strip()
    if re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts):
        return ts
    return fallback


def parse_cap_xml(xml_text: str, source_url: str) -> dict[str, Any] | None:
    """Parse a CAP 1.2 XML document and return an AlertModel-compatible dict.

    Returns None if the alert should be ignored (Test/Exercise/Draft).
    Polygons are returned in GeoJSON [lon, lat] order.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Failed to parse CAP XML from %s: %s", source_url, exc)
        return None

    # Strip namespaces
    for elem in root.iter():
        elem.tag = _strip_ns(elem.tag)

    identifier = root.findtext("identifier", f"sachet-{uuid.uuid4()}")
    sender = root.findtext("sender", "NDMA-SACHET")
    sent = _iso(root.findtext("sent"), now_iso)
    status = root.findtext("status", "Actual")
    msg_type = root.findtext("msgType", "Alert")
    references = root.findtext("references", "")

    if status in IGNORED_STATUSES:
        logger.info("Ignoring CAP message with status=%s id=%s", status, identifier)
        return None

    info = root.find("info")
    if info is None:
        logger.warning("CAP alert %s has no <info> element, skipping.", identifier)
        return None

    event = info.findtext("event", "Weather Advisory")
    severity_raw = info.findtext("severity", "Unknown")
    severity = severity_raw if severity_raw in SEVERITY_LEVEL_MAP else "Unknown"
    urgency_raw = info.findtext("urgency", "Unknown")
    certainty_raw = info.findtext("certainty", "Unknown")
    onset = _iso(info.findtext("onset"), sent)
    expires = _iso(info.findtext("expires"), now_iso)
    headline = info.findtext("headline", "")
    description = info.findtext("description", headline)
    language = info.findtext("language", "en-IN")
    lang_code = language.split("-")[0] if "-" in language else language

    # Areas + polygon conversion
    areas: list[dict[str, Any]] = []
    for area_elem in info.findall("area"):
        area_desc = area_elem.findtext("areaDesc", "India")
        poly_text = area_elem.findtext("polygon", "")
        geojson_coords: list[list[float]] = []
        if poly_text:
            for pair in poly_text.strip().split():
                parts = pair.split(",")
                if len(parts) >= 2:
                    try:
                        lat, lon = float(parts[0]), float(parts[1])
                        geojson_coords.append([lon, lat])  # GeoJSON order
                    except ValueError:
                        pass
        areas.append({
            "areaDesc": area_desc,
            "polygon": poly_text,
            "geojson_coords": geojson_coords,
        })

    if not areas:
        areas = [{"areaDesc": "India Region", "polygon": "", "geojson_coords": []}]

    # Urgency / certainty normalization
    valid_urgencies = {"Immediate", "Expected", "Future", "Past", "Unknown"}
    valid_certainties = {"Observed", "Likely", "Possible", "Unlikely", "Unknown"}
    urgency = urgency_raw if urgency_raw in valid_urgencies else "Unknown"
    certainty = certainty_raw if certainty_raw in valid_certainties else "Unknown"

    level = severity_to_level(severity)

    return {
        "id": f"urn:oid:2.49.0.1.356.sachet.{re.sub(r'[^a-zA-Z0-9]', '.', identifier)}",
        "sender": sender,
        "sent": sent,
        "status": status,
        "msg_type": msg_type,
        "hazard": event,
        "severity": severity,
        "urgency": urgency,
        "certainty": certainty,
        "onset": onset,
        "expires": expires,
        "areas": areas,
        "text_by_language": {lang_code: description or event},
        "source_url": source_url,
        "authority_tier": 1,
        "level": level,
        # Non-schema metadata for ingest bookkeeping
        "_references": references,
    }


class SachetCAPAdapter:
    """Adapter for the NDMA SACHET CAP 1.2 alert feeds."""

    ALLOWLISTED = ALLOWLISTED_DOMAINS

    def is_sender_allowed(self, url: str) -> bool:
        """Return True only if the CAP XML URL is from an allowlisted domain."""
        # Strip protocol
        stripped = re.sub(r"^https?://", "", url)
        host = stripped.split("/")[0].split("?")[0]
        return host in self.ALLOWLISTED

    def should_ignore_message(self, status: str, msg_type: str) -> bool:  # noqa: ARG002
        """Return True if the message should be silently ignored in production."""
        return status in IGNORED_STATUSES

    def cap_polygon_to_geojson(self, polygon: str) -> list[list[float]]:
        """Convert CAP polygon string (lat,lon pairs) to GeoJSON coordinate list [lon, lat]."""
        if not polygon or not polygon.strip():
            return []
        coords: list[list[float]] = []
        for pair in polygon.strip().split():
            parts = pair.split(",")
            if len(parts) >= 2:
                try:
                    lat, lon = float(parts[0]), float(parts[1])
                    coords.append([lon, lat])
                except ValueError:
                    pass
        return coords

    def parse(self, xml_text: str, source_url: str) -> dict[str, Any] | None:
        """Parse CAP XML text to an AlertModel-compatible dict. Returns None if ignored."""
        if not self.is_sender_allowed(source_url):
            logger.warning("Rejecting CAP alert from non-allowlisted URL: %s", source_url)
            return None
        return parse_cap_xml(xml_text=xml_text, source_url=source_url)

    def fetch_rss_items(self, rss_xml: str) -> list[dict[str, str]]:
        """Parse SACHET RSS feed and return a list of {link, title} dicts."""
        try:
            root = ET.fromstring(rss_xml)
        except ET.ParseError:
            return []
        items = []
        for item in root.findall(".//item"):
            link = item.findtext("link", "").strip()
            title = item.findtext("title", "").strip()
            if link and self.is_sender_allowed(link):
                items.append({"link": link, "title": title})
        return items
