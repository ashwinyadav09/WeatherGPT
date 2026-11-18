from __future__ import annotations

import datetime as dt
from typing import Any

from pydantic import BaseModel, Field


class ThresholdConfig(BaseModel):
    heat_index_c: float | None = Field(None, description="Trigger alert if Heat Index >= threshold in degC")
    rain_rate_mm_hr: float | None = Field(None, description="Trigger alert if rain intensity >= threshold in mm/hr")
    lightning_warning: bool | None = Field(None, description="Trigger alert if lightning/thunderstorm detected")
    wind_gust_kmh: float | None = Field(None, description="Trigger alert if wind gust >= threshold in km/h")


class SubscriptionCreateRequest(BaseModel):
    subscriber_name: str = Field(..., min_length=2, description="Name of municipal or smart-city entity")
    place_id: str = Field(..., min_length=2, description="Target city/place identifier")
    webhook_url: str = Field(..., min_length=8, description="Target webhook URL (HTTPS/HTTP)")
    secret: str | None = Field(None, description="Shared secret for HMAC-SHA256 signature verification")
    thresholds: ThresholdConfig
    cooldown_minutes: int = Field(15, ge=1, le=1440, description="Minimum quiet time between successive alerts to prevent flooding")


class ThresholdSubscription(BaseModel):
    id: str
    subscriber_name: str
    place_id: str
    webhook_url: str
    secret: str | None = None
    thresholds: ThresholdConfig
    cooldown_minutes: int
    created_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    last_triggered_at: dt.datetime | None = None
    is_active: bool = True


class SensorObservation(BaseModel):
    place_id: str
    temperature_c: float
    relative_humidity_pct: float = Field(..., ge=0, le=100)
    rain_rate_mm_hr: float = 0.0
    lightning_detected: bool = False
    wind_gust_kmh: float = 0.0
    timestamp: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))


class WebhookDeliveryLog(BaseModel):
    id: str
    subscription_id: str
    subscriber_name: str
    place_id: str
    webhook_url: str
    triggered_thresholds: list[str]
    dispatched_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    status_code: int | None = None
    success: bool
    latency_ms: int
    payload: dict[str, Any]
    error: str | None = None
