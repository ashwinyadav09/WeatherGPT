from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from services.api.app.config import Settings

logger = structlog.get_logger()

ROOT = Path(__file__).resolve().parents[5]
FIXTURES_DIR = ROOT / "eval" / "fixtures" / "imd"

COASTAL_ALIASES = {
    "konkan": "konkan_goa",
    "goa": "konkan_goa",
    "mumbai": "konkan_goa",
    "maharashtra": "konkan_goa",
    "कोंकण": "konkan_goa",
    "मुंबई": "konkan_goa",
    "north gujarat": "north_gujarat",
    "kutch": "north_gujarat",
    "kandla": "north_gujarat",
    "उत्तरी गुजरात": "north_gujarat",
    "south gujarat": "south_gujarat",
    "surat": "south_gujarat",
    "khambhat": "south_gujarat",
    "दक्षणी गुजरात": "south_gujarat",
    "tamil nadu": "tamil_nadu",
    "chennai": "tamil_nadu",
    "puducherry": "tamil_nadu",
    "coromandel": "tamil_nadu",
    "तमिलनाडु": "tamil_nadu",
    "चेन्नई": "tamil_nadu",
    "west bengal": "west_bengal",
    "bengal": "west_bengal",
    "kolkata": "west_bengal",
    "digha": "west_bengal",
    "sundarbans": "west_bengal",
    "पश्चिम बंगाल": "west_bengal",
    "kerala": "kerala",
    "kochi": "kerala",
    "lakshadweep": "kerala",
    "malabar": "kerala",
    "केरल": "kerala",
    "कोच्चि": "kerala",
}


class MarineAdapter:
    """Adapter for IMD Coastal Weather Bulletins and Fishermen Warnings in collaboration with INCOIS.

    Follows ADR 0007: contract-first with documented-sample fixtures until live key arrives.
    Always attaches mandatory non-briefing safety notice.
    """

    def __init__(
        self,
        fixture_path: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        from services.api.app.config import settings as app_settings
        self.fixture_path = fixture_path or (FIXTURES_DIR / "marine_bulletin_sample.json")
        self.settings = settings or app_settings
        self._bulletin_cache: dict[str, Any] | None = None
        self._load_fixtures()

    def _load_fixtures(self) -> None:
        if self.fixture_path.exists():
            try:
                with self.fixture_path.open("r", encoding="utf-8") as f:
                    self._bulletin_cache = json.load(f)
            except Exception as e:
                logger.warning("marine_fixture_load_failed", path=str(self.fixture_path), error=str(e))
                self._bulletin_cache = None

    def normalize_area(self, area_input: str) -> str:
        clean = area_input.strip().lower()
        for k, v in COASTAL_ALIASES.items():
            if k in clean:
                return v
        return "konkan_goa"

    async def get_marine_bulletin(
        self,
        area: str = "konkan_goa",
        language: str = "en",
    ) -> dict[str, Any]:
        """Fetches coastal bulletin, sea condition and fishermen warning for a coastal sector."""
        norm_area = self.normalize_area(area)

        # In default config (AGROMET_FIXTURE_ENABLED=false), never return fixture bulletins
        if not self.settings.agromet_fixture_enabled:
            return {
                "status": "unavailable",
                "area_id": norm_area,
                "area_name": norm_area.replace("_", " ").title(),
                "weather": "",
                "message": "Official coastal bulletins are currently unavailable.",
                "source": "Coastal Weather Services / INCOIS",
                "authority_tier": 1,
                "provenance": "spec-only",
            }

        if not self._bulletin_cache:
            self._load_fixtures()

        bulletin = self._bulletin_cache or {}
        areas = bulletin.get("areas", {})
        area_data = areas.get(norm_area, areas.get("konkan_goa", {}))

        is_hi = language == "hi"
        area_display = area_data.get("area_name_hi" if is_hi else "area_name", norm_area.replace("_", " ").title())
        weather_desc = area_data.get("weather_hi" if is_hi else "weather", "")

        safety_banner = bulletin.get("safety_banner", {
            "text_en": (
                "SAFETY NOTICE: For official navigation, port, and high-seas operations, refer directly to official IMD / INCOIS marine bulletins. "
                "Fishermen are strictly advised to adhere to official coastal authority warnings before venturing into the sea."
            ),
            "text_hi": (
                "सुरक्षा सूचना: आधिकारिक नौवहन, बंदरगाह और समुद्री संचालन के लिए केवल भारतीय मौसम विज्ञान विभाग (IMD) एवं INCOIS के आधिकारिक बुलेटिन देखें। "
                "मछुआरों को समुद्र में जाने से पहले तटीय प्रशासन की चेतावनियों का अनिवार्य रूप से पालन करने की सलाह दी जाती है।"
            ),
            "authority": "India Meteorological Department (IMD) & INCOIS",
            "type": "informational-safety-notice",
        })

        return {
            "status": "success",
            "area_id": norm_area,
            "area_name": area_display,
            "sea_area": area_data.get("sea_area", ""),
            "weather": weather_desc,
            "visibility": area_data.get("visibility", ""),
            "wind": area_data.get("wind", ""),
            "sea_condition": area_data.get("sea_condition", "Moderate"),
            "port_warning": area_data.get("port_warning", "No warning signal hoisted"),
            "fishermen_warning": area_data.get("fishermen_warning", {
                "status": "no_warning",
                "level": "green",
                "warning_en": "No fishermen warning active.",
                "warning_hi": "कोई चेतावनी नहीं है।",
            }),
            "safety_banner": safety_banner,
            "source": bulletin.get("organization", "IMD Marine Weather Services / INCOIS"),
            "authority_tier": 1,
            "issue_time": bulletin.get("issue_time", "2026-11-17T12:00:00+05:30"),
            "valid_until": bulletin.get("valid_until", "2026-11-18T12:00:00+05:30"),
            "provenance": bulletin.get("_provenance", "documented-sample"),
            "imd_key_status": "live" if self.settings.imd_enabled else "pending_key_contract_fixture",
        }
