from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from services.api.app.modules.smart_city.models import (
    SensorObservation,
    SubscriptionCreateRequest,
    ThresholdSubscription,
    WebhookDeliveryLog,
)
from services.api.app.modules.smart_city.service import (
    compute_heat_index_c,
    smart_city_service,
)

router = APIRouter(prefix="/smart-city", tags=["smart-city"])


@router.post("/subscriptions", response_model=ThresholdSubscription, status_code=status.HTTP_201_CREATED)
async def create_subscription(req: SubscriptionCreateRequest) -> ThresholdSubscription:
    """Subscribes a smart city operator or dashboard to threshold alerts delivered via webhook."""
    return smart_city_service.register_subscription(req)


@router.get("/subscriptions", response_model=list[ThresholdSubscription])
async def list_subscriptions(place_id: str | None = Query(None, description="Filter by place ID")) -> list[ThresholdSubscription]:
    """Lists active smart-city threshold webhook subscriptions."""
    return smart_city_service.get_subscriptions(place_id=place_id)


@router.delete("/subscriptions/{sub_id}")
async def delete_subscription(sub_id: str) -> dict[str, Any]:
    """Cancels a threshold webhook subscription."""
    deleted = smart_city_service.delete_subscription(sub_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subscription '{sub_id}' not found")
    return {"success": True, "subscription_id": sub_id}


@router.post("/evaluate")
async def evaluate_sensor_readings(obs: SensorObservation) -> dict[str, Any]:
    """Evaluates incoming city weather/sensor observations against subscriptions and dispatches webhooks."""
    return await smart_city_service.evaluate_observation(obs)


@router.get("/deliveries", response_model=list[WebhookDeliveryLog])
async def get_deliveries(limit: int = Query(50, ge=1, le=500)) -> list[WebhookDeliveryLog]:
    """Retrieves smart-city webhook delivery audit logs."""
    return smart_city_service.get_delivery_logs(limit=limit)


@router.get("/heat-index")
async def calculate_heat_index(
    temp_c: float = Query(..., ge=-20, le=60, description="Ambient temperature in degC"),
    rh_pct: float = Query(..., ge=0, le=100, description="Relative humidity in percentage"),
) -> dict[str, Any]:
    """Computes Heat Index based on ambient temperature and relative humidity."""
    hi_c = compute_heat_index_c(temp_c, rh_pct)
    return {
        "temperature_c": temp_c,
        "relative_humidity_pct": rh_pct,
        "heat_index_c": hi_c,
        "category": (
            "Extreme Danger"
            if hi_c >= 54.0
            else (
                "Danger"
                if hi_c >= 41.0
                else ("Extreme Caution" if hi_c >= 32.0 else ("Caution" if hi_c >= 27.0 else "Normal"))
            )
        ),
    }
