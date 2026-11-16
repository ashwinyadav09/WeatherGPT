from __future__ import annotations

from typing import Any

from packages.contracts.validator import validate_schema


def validate_evidence_packet_dict(data: dict[str, Any]) -> None:
    validate_schema("evidence_packet", data)


def validate_alert_dict(data: dict[str, Any]) -> None:
    validate_schema("alert", data)


def validate_place_dict(data: dict[str, Any]) -> None:
    validate_schema("place", data)
