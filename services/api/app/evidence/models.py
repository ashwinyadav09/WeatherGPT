from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field


class PlaceReference(BaseModel):
    id: str
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class ValueItem(BaseModel):
    variable: str
    value: float | str | None
    unit: str
    step: int | str | None = None


class Uncertainty(BaseModel):
    type: str
    value: float | str


class EvidencePacket(BaseModel):
    id: str
    source: str
    authority_tier: int = Field(ge=1, le=5)
    provenance: Literal["live", "live-recorded", "documented-sample", "spec-only", "synthetic"]
    issued_at: dt.datetime
    valid_from: dt.datetime
    valid_to: dt.datetime
    place: PlaceReference
    values: list[ValueItem]
    uncertainty: Uncertainty | None = None
    attribution: str
    fetched_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))


class PlaceModel(BaseModel):
    id: str
    kind: Literal["district", "block", "gp", "village", "station", "point"]
    names: dict[str, str]
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    elevation: float | None = None
    state: str | None = None
    district: str | None = None


class AlertModel(BaseModel):
    id: str
    sender: str
    sent: dt.datetime
    status: str
    msg_type: str
    hazard: str
    severity: Literal["Extreme", "Severe", "Moderate", "Minor", "Unknown"]
    urgency: Literal["Immediate", "Expected", "Future", "Past", "Unknown"]
    certainty: Literal["Observed", "Likely", "Possible", "Unlikely", "Unknown"]
    onset: dt.datetime
    expires: dt.datetime
    areas: list[dict[str, Any]]
    text_by_language: dict[str, str]
    source_url: str
    authority_tier: int = 1
    level: Literal["green", "yellow", "orange", "red"]
