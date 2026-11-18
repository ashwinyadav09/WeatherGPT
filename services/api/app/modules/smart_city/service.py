from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import time
import uuid
from typing import Any

import httpx
import structlog

from services.api.app.modules.smart_city.models import (
    SensorObservation,
    SubscriptionCreateRequest,
    ThresholdSubscription,
    WebhookDeliveryLog,
)

logger = structlog.get_logger()


def compute_heat_index_c(temp_c: float, rh_pct: float) -> float:
    """Computes Heat Index in Celsius using the standard NWS/NOAA Rothfusz regression equation."""
    if temp_c < 20.0 or rh_pct < 20.0:
        return temp_c

    # Convert to Fahrenheit
    tf = temp_c * 9.0 / 5.0 + 32.0
    rh = rh_pct

    # Simple Steadman equation
    hi_simple = 0.5 * (tf + 61.0 + ((tf - 68.0) * 1.2) + (rh * 0.094))
    if hi_simple < 80.0:
        hi_f = hi_simple
    else:
        # Full Rothfusz regression
        c1 = -42.379
        c2 = 2.04901523
        c3 = 10.14333127
        c4 = -0.22475541
        c5 = -0.00683783
        c6 = -0.05481717
        c7 = 0.00122874
        c8 = 0.00085282
        c9 = -0.00000199

        hi_f = (
            c1
            + c2 * tf
            + c3 * rh
            + c4 * tf * rh
            + c5 * (tf**2)
            + c6 * (rh**2)
            + c7 * (tf**2) * rh
            + c8 * tf * (rh**2)
            + c9 * (tf**2) * (rh**2)
        )

        # Adjustments
        if rh < 13.0 and 80.0 <= tf <= 112.0:
            adj = ((13.0 - rh) / 4.0) * (((17.0 - abs(tf - 95.0)) / 17.0) ** 0.5)
            hi_f -= adj
        elif rh > 85.0 and 80.0 <= tf <= 87.0:
            adj = ((rh - 85.0) / 10.0) * ((87.0 - tf) / 5.0)
            hi_f += adj

    # Convert back to Celsius
    hi_c = (hi_f - 32.0) * 5.0 / 9.0
    return round(hi_c, 1)


class SmartCityService:
    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._subscriptions: dict[str, ThresholdSubscription] = {}
        self._delivery_logs: list[WebhookDeliveryLog] = []
        self._client = http_client

    def register_subscription(self, req: SubscriptionCreateRequest) -> ThresholdSubscription:
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        sub = ThresholdSubscription(
            id=sub_id,
            subscriber_name=req.subscriber_name,
            place_id=req.place_id.lower().strip(),
            webhook_url=req.webhook_url,
            secret=req.secret,
            thresholds=req.thresholds,
            cooldown_minutes=req.cooldown_minutes,
        )
        self._subscriptions[sub_id] = sub
        logger.info("smart_city_subscription_registered", sub_id=sub_id, place_id=sub.place_id)
        return sub

    def get_subscriptions(self, place_id: str | None = None) -> list[ThresholdSubscription]:
        subs = list(self._subscriptions.values())
        if place_id:
            subs = [s for s in subs if s.place_id == place_id.lower().strip()]
        return subs

    def delete_subscription(self, sub_id: str) -> bool:
        if sub_id in self._subscriptions:
            del self._subscriptions[sub_id]
            logger.info("smart_city_subscription_deleted", sub_id=sub_id)
            return True
        return False

    def get_delivery_logs(self, limit: int = 50) -> list[WebhookDeliveryLog]:
        return self._delivery_logs[-limit:]

    async def evaluate_observation(self, obs: SensorObservation) -> dict[str, Any]:
        """Evaluates sensor readings against active city subscriptions and fires webhooks."""
        place_id = obs.place_id.lower().strip()
        heat_index = compute_heat_index_c(obs.temperature_c, obs.relative_humidity_pct)
        now = dt.datetime.now(dt.timezone.utc)

        matching_subs = [s for s in self._subscriptions.values() if s.is_active and s.place_id == place_id]
        triggered_deliveries: list[WebhookDeliveryLog] = []
        suppressed_count = 0

        for sub in matching_subs:
            # 1. Check cooldown rate limiting
            if sub.last_triggered_at:
                elapsed_sec = (now - sub.last_triggered_at).total_seconds()
                cooldown_sec = sub.cooldown_minutes * 60.0
                if elapsed_sec < cooldown_sec:
                    suppressed_count += 1
                    logger.info(
                        "webhook_delivery_suppressed_cooldown",
                        sub_id=sub.id,
                        elapsed_sec=elapsed_sec,
                        cooldown_sec=cooldown_sec,
                    )
                    continue

            # 2. Evaluate threshold violations
            violations: list[str] = []
            th = sub.thresholds

            if th.heat_index_c is not None and heat_index >= th.heat_index_c:
                violations.append(f"Heat Index {heat_index}°C exceeded threshold {th.heat_index_c}°C")

            if th.rain_rate_mm_hr is not None and obs.rain_rate_mm_hr >= th.rain_rate_mm_hr:
                violations.append(f"Rain rate {obs.rain_rate_mm_hr} mm/hr exceeded threshold {th.rain_rate_mm_hr} mm/hr")

            if th.lightning_warning and obs.lightning_detected:
                violations.append("Lightning / thunderstorm activity detected in area")

            if th.wind_gust_kmh is not None and obs.wind_gust_kmh >= th.wind_gust_kmh:
                violations.append(f"Wind gust {obs.wind_gust_kmh} km/h exceeded threshold {th.wind_gust_kmh} km/h")

            if not violations:
                continue

            # 3. Formulate webhook payload
            delivery_id = f"del_{uuid.uuid4().hex[:12]}"
            payload = {
                "event": "threshold_alert",
                "delivery_id": delivery_id,
                "timestamp": now.isoformat(),
                "subscription_id": sub.id,
                "subscriber_name": sub.subscriber_name,
                "place_id": place_id,
                "readings": {
                    "temperature_c": obs.temperature_c,
                    "relative_humidity_pct": obs.relative_humidity_pct,
                    "heat_index_c": heat_index,
                    "rain_rate_mm_hr": obs.rain_rate_mm_hr,
                    "lightning_detected": obs.lightning_detected,
                    "wind_gust_kmh": obs.wind_gust_kmh,
                },
                "triggered_thresholds": violations,
            }

            headers = {
                "Content-Type": "application/json",
                "X-WeatherGPT-Event": "threshold_alert",
                "X-WeatherGPT-Delivery-ID": delivery_id,
                "X-WeatherGPT-Place": place_id,
            }

            # Optional HMAC-SHA256 signature
            payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
            if sub.secret:
                sig = hmac.new(sub.secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
                headers["X-WeatherGPT-Signature-256"] = sig

            # 4. Dispatch webhook
            status_code = None
            success = False
            error_msg = None
            start_t = time.time()

            try:
                if self._client:
                    resp = await self._client.post(sub.webhook_url, content=payload_bytes, headers=headers, timeout=5.0)
                    status_code = resp.status_code
                    success = resp.status_code in (200, 201, 202, 204)
                else:
                    async with httpx.AsyncClient(timeout=5.0) as cli:
                        resp = await cli.post(sub.webhook_url, content=payload_bytes, headers=headers)
                        status_code = resp.status_code
                        success = resp.status_code in (200, 201, 202, 204)
            except Exception as e:
                error_msg = str(e)
                logger.warning("webhook_dispatch_failed", url=sub.webhook_url, error=str(e))

            latency_ms = int((time.time() - start_t) * 1000)

            # 5. Record delivery log & update trigger time
            log_entry = WebhookDeliveryLog(
                id=delivery_id,
                subscription_id=sub.id,
                subscriber_name=sub.subscriber_name,
                place_id=place_id,
                webhook_url=sub.webhook_url,
                triggered_thresholds=violations,
                dispatched_at=now,
                status_code=status_code,
                success=success,
                latency_ms=latency_ms,
                payload=payload,
                error=error_msg,
            )
            self._delivery_logs.append(log_entry)
            triggered_deliveries.append(log_entry)

            sub.last_triggered_at = now

        return {
            "place_id": place_id,
            "heat_index_c": heat_index,
            "matching_subscriptions": len(matching_subs),
            "triggered_deliveries": len(triggered_deliveries),
            "suppressed_by_cooldown": suppressed_count,
            "deliveries": [d.model_dump(mode="json") for d in triggered_deliveries],
        }


smart_city_service = SmartCityService()
