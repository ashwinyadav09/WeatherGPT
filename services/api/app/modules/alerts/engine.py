from __future__ import annotations

import datetime as dt

from services.api.app.evidence.models import AlertModel


class AlertEngine:
    def __init__(self) -> None:
        self._alerts: list[AlertModel] = []

    async def get_active_alerts(self, place_id: str | None = None) -> list[AlertModel]:
        now = dt.datetime.now(dt.timezone.utc)
        # Filter active non-expired alerts
        active = [a for a in self._alerts if a.expires > now]
        return active

    def ingest_sample_alert(self, alert: AlertModel) -> None:
        self._alerts.append(alert)
