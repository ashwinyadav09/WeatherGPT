from __future__ import annotations

import httpx
import pytest

from services.api.app.modules.smart_city.models import (
    SensorObservation,
    SubscriptionCreateRequest,
    ThresholdConfig,
)
from services.api.app.modules.smart_city.service import (
    SmartCityService,
    compute_heat_index_c,
)


def test_heat_index_computation() -> None:
    # Ambient temp < 20C returns same temp
    assert compute_heat_index_c(18.0, 50.0) == 18.0

    # Mild temperature e.g. 26C, 60% RH -> ~26.4C
    hi_mild = compute_heat_index_c(26.0, 60.0)
    assert 25.0 <= hi_mild <= 28.0

    # High temperature & humidity e.g. 35C, 70% RH -> severe heat index (> 48C)
    hi_severe = compute_heat_index_c(35.0, 70.0)
    assert hi_severe >= 48.0


@pytest.mark.asyncio
async def test_smart_city_subscription_lifecycle_and_evaluation() -> None:
    dispatched_requests = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        dispatched_requests.append(request)
        return httpx.Response(200, json={"received": True})

    transport = httpx.MockTransport(mock_handler)
    mock_client = httpx.AsyncClient(transport=transport)

    service = SmartCityService(http_client=mock_client)

    # 1. Register subscription
    req = SubscriptionCreateRequest(
        subscriber_name="Pune Municipal Corporation Control Room",
        place_id="pune",
        webhook_url="https://mock-pmc.gov.in/webhooks/weather",
        secret="test-hmac-secret-key",
        thresholds=ThresholdConfig(
            heat_index_c=40.0,
            rain_rate_mm_hr=15.0,
            lightning_warning=True,
        ),
        cooldown_minutes=15,
    )
    sub = service.register_subscription(req)
    assert sub.id.startswith("sub_")
    assert sub.place_id == "pune"

    # 2. Check listing
    subs = service.get_subscriptions("pune")
    assert len(subs) == 1
    assert subs[0].id == sub.id

    # 3. Observation below thresholds -> No webhook
    normal_obs = SensorObservation(
        place_id="pune",
        temperature_c=28.0,
        relative_humidity_pct=40.0,
        rain_rate_mm_hr=2.0,
        lightning_detected=False,
    )
    res_normal = await service.evaluate_observation(normal_obs)
    assert res_normal["triggered_deliveries"] == 0
    assert len(dispatched_requests) == 0

    # 4. Observation exceeding rain & heat index thresholds -> Webhook fired
    severe_obs = SensorObservation(
        place_id="pune",
        temperature_c=36.0,
        relative_humidity_pct=75.0,  # HI will exceed 40C
        rain_rate_mm_hr=25.0,         # Exceeds 15 mm/hr
        lightning_detected=True,
    )
    res_severe = await service.evaluate_observation(severe_obs)
    assert res_severe["triggered_deliveries"] == 1
    assert len(dispatched_requests) == 1

    last_req = dispatched_requests[-1]
    assert last_req.headers["X-WeatherGPT-Event"] == "threshold_alert"
    assert "X-WeatherGPT-Delivery-ID" in last_req.headers
    assert "X-WeatherGPT-Signature-256" in last_req.headers  # HMAC signed

    # 5. Subsequent immediate severe observation -> Suppressed by 15-minute cooldown
    res_cooldown = await service.evaluate_observation(severe_obs)
    assert res_cooldown["triggered_deliveries"] == 0
    assert res_cooldown["suppressed_by_cooldown"] == 1
    assert len(dispatched_requests) == 1  # No second webhook dispatched

    # 6. Delivery logs audit
    logs = service.get_delivery_logs()
    assert len(logs) == 1
    assert logs[0].success is True
    assert logs[0].status_code == 200
    assert len(logs[0].triggered_thresholds) >= 2

    # 7. Delete subscription
    assert service.delete_subscription(sub.id) is True
    assert len(service.get_subscriptions("pune")) == 0
