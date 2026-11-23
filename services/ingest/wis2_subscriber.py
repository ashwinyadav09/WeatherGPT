"""NOT ENABLED: WIS2 subscriber is not wired into the production stack.

Retained for architectural reference only. Ingest of official warnings is
handled exclusively by the SACHET RSS/CAP poller.
"""
from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WIS2Message:
    id: str
    topic: str
    data_id: str
    geometry: dict[str, Any]
    links: list[dict[str, str]]
    received_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))


class WIS2Subscriber:
    """Subscriber for WMO Information System 2.0 (WIS2) notification feeds.

    NOT ENABLED: This subscriber is not wired into the production stack.
    It remains in the repository for future reference. Do not instantiate
    in production code; use the SACHET RSS poller instead.

    Listens to MQTT broker topics (e.g. origin/a/wis2/in-imd/#) or receives
    real-time notifications from a Global Broker.
    """

    def __init__(self, broker_host: str = "globalbroker.meteo.fr", port: int = 8883) -> None:
        self.broker_host = broker_host
        self.port = port
        # _connected starts False; set to True only after a real MQTT handshake.
        self._connected = False
        self._started_at = dt.datetime.now(dt.timezone.utc)
        self._messages: list[WIS2Message] = []
        self._topics_subscribed = [
            "origin/a/wis2/in-imd/#",
            "origin/a/wis2/in-ncmrwf/#",
            "origin/a/wis2/ecmwf/#",
        ]

    def is_connected(self) -> bool:
        return self._connected

    @property
    def messages_received_count(self) -> int:
        return len(self._messages)

    def process_message(self, topic: str, payload: dict[str, Any]) -> WIS2Message:
        msg_id = payload.get("id", f"wis2-msg-{len(self._messages) + 1}")
        props = payload.get("properties", {})
        data_id = props.get("data_id", "unknown")
        geometry = payload.get("geometry", {})
        links = payload.get("links", [])

        msg = WIS2Message(
            id=msg_id,
            topic=topic,
            data_id=data_id,
            geometry=geometry,
            links=links,
        )
        self._messages.append(msg)
        logger.info("Processed WIS2 notification for topic: %s (data_id: %s)", topic, data_id)
        return msg

    def get_uptime_report(self) -> dict[str, Any]:
        return {
            "broker_host": self.broker_host,
            "connected": self._connected,
            "uptime_seconds": 0.0,
            "uptime_pct": "NOT MEASURED",
            "messages_received": len(self._messages),
            "topics": self._topics_subscribed,
            "status": "healthy" if self._connected else "disconnected",
        }
