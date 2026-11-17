from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from services.api.app.evidence.models import AlertModel
from services.api.app.modules.alerts.engine import AlertEngine

router = APIRouter(tags=["alerts"])
_engine = AlertEngine()


class PushKeys(BaseModel):
    p256dh: str | None = None
    auth: str | None = None


class PushSubscriptionModel(BaseModel):
    endpoint: str
    keys: PushKeys | dict[str, str] = Field(default_factory=dict)
    places: list[str] = Field(default_factory=list)
    severities: list[str] = Field(default_factory=lambda: ["Extreme", "Severe", "Moderate"])
    quiet_hours: dict[str, str] | None = None


_subscriptions: dict[str, PushSubscriptionModel] = {}


@router.get("/alerts", response_model=list[AlertModel])
async def get_alerts(
    place_id: str | None = Query(None, description="Filter alerts by place"),
    lat: float | None = Query(None, description="Latitude for polygon matching"),
    lon: float | None = Query(None, description="Longitude for polygon matching"),
    district: str | None = Query(None, description="District name for fallback matching"),
) -> Any:
    if lat is not None and lon is not None:
        return _engine.match_alerts(lat=lat, lon=lon, district=district)
    return await _engine.get_active_alerts(place_id=place_id)


@router.post("/push/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_push(sub: PushSubscriptionModel) -> dict[str, Any]:
    _subscriptions[sub.endpoint] = sub
    return {
        "status": "subscribed",
        "endpoint": sub.endpoint,
        "places": sub.places,
        "severities": sub.severities,
    }


@router.delete("/push/subscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_push(
    endpoint: str = Query(..., description="Push subscription endpoint URL to delete"),
) -> dict[str, Any]:
    if endpoint in _subscriptions:
        del _subscriptions[endpoint]
        return {"status": "unsubscribed", "endpoint": endpoint}
    raise HTTPException(status_code=404, detail="Subscription not found")
