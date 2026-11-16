from __future__ import annotations

from typing import Any


class AdvisoryEngine:
    async def get_advisory(self, place_id: str, domain: str, crop: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "id": "adv_001",
                "place_id": place_id,
                "domain": domain,
                "crop": crop,
                "headline": f"Official {domain.title()} Advisory",
                "guidance": "Follow local safety instructions and stay hydrated during warm periods.",
                "source": "IMD Agromet Advisory Service",
            }
        ]
