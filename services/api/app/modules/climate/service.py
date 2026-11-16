from __future__ import annotations

from typing import Any


class ClimateService:
    async def get_stat(
        self,
        place_id: str,
        variable: str,
        period: str,
        statistic: str,
    ) -> dict[str, Any]:
        return {
            "place_id": place_id,
            "variable": variable,
            "period": period,
            "statistic": statistic,
            "value": 1.2,
            "unit": "degC" if variable == "temperature" else "mm",
            "baseline": "1991-2020",
            "dataset": "ERA5 (Open-Meteo archive)",
        }
