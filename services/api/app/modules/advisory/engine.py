from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
import yaml

from services.api.app.modules.alerts.engine import AlertEngine

logger = structlog.get_logger()

ROOT = Path(__file__).resolve().parents[5]
GUIDANCE_DIR = ROOT / "seeds" / "guidance"

EVACUATION_PATTERNS = [
    re.compile(r"\b(?:should\s+(?:i|we)\s+evacuate|evacuate\s+or\s+stay|must\s+(?:i|we)\s+leave|need\s+to\s+evacuate|shall\s+we\s+evacuate)\b", re.IGNORECASE),
    re.compile(r"(?:घर\s*खाली\s*कर|निकल\s*जाएं|घर\s*छोड़|सुरक्षित\s*स्थान\s*पर\s*चले|इवैक्युएट|खाली\s*करना\s*पड़ेगा)", re.IGNORECASE),
]

PESTICIDE_PATTERNS = [
    re.compile(r"\b(?:pesticide\s+dose|insecticide\s+dose|fungicide\s+dose|spray\s+dose|chemical\s+dose|how\s+much\s+(?:pesticide|spray|insecticide))\b", re.IGNORECASE),
    re.compile(r"(?:कीटनाशक\s*की\s*मात्रा|कितनी\s*दवा\s*छिड़क|कीटनाशक\s*का\s*डोज|दवा\s*का\s*छिड़काव\s*कितना)", re.IGNORECASE),
]


class AdvisoryEngine:
    """Advisory Engine for official NDMA/IMD heat and cold wave guidance, with safety redirects."""

    def __init__(self, alert_engine: AlertEngine | None = None) -> None:
        self.alert_engine = alert_engine or AlertEngine()
        self._guidance_cache: dict[str, dict[str, Any]] = {}
        self._load_guidance_library()

    def _load_guidance_library(self) -> None:
        """Loads curated official guidance files from seeds/guidance/."""
        if not GUIDANCE_DIR.exists():
            return
        for file in GUIDANCE_DIR.glob("*.yaml"):
            try:
                with file.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "hazard" in data:
                        self._guidance_cache[data["hazard"]] = data
            except Exception as e:
                logger.warning("guidance_load_failed", file=str(file), error=str(e))

    def has_active_warning(self, hazard: str, active_alerts: list[Any]) -> bool:
        """Checks if an official warning applies for the given hazard."""
        norm_hazard = hazard.lower().replace("_", " ").strip()
        for a in active_alerts:
            a_hazard = getattr(a, "hazard", "").lower()
            if norm_hazard in a_hazard or a_hazard in norm_hazard:
                return True
        return False

    async def get_advisory(
        self,
        place_id: str,
        domain: str = "heat_wave",
        language: str = "en",
        force_check_warnings: bool = True,
    ) -> list[dict[str, Any]]:
        """Returns official guidance cards.

        Cards appear ONLY when official warnings apply.
        """
        # Normalize domain to hazard key
        hazard_key = "heat_wave" if "heat" in domain.lower() else ("cold_wave" if "cold" in domain.lower() else domain.lower())

        if hazard_key not in self._guidance_cache:
            self._load_guidance_library()

        data = self._guidance_cache.get(hazard_key)
        if not data:
            return []

        # Enforce Rule: Cards appear only when official warnings apply
        if force_check_warnings:
            active_alerts = await self.alert_engine.get_active_alerts(place_id=place_id)
            if not self.has_active_warning(hazard_key, active_alerts):
                # No official warning active for this hazard; suppress guidance card
                logger.info("guidance_suppressed_no_active_warning", place_id=place_id, hazard=hazard_key)
                return []

        entries = data.get("entries", {})
        lang_entry = entries.get(language, entries.get("en", {}))
        if not lang_entry:
            return []

        card = {
            "id": lang_entry.get("id", f"guidance_{hazard_key}_{language}"),
            "hazard": hazard_key,
            "domain": domain,
            "place_id": place_id,
            "title": lang_entry.get("title", f"Official {hazard_key.title()} Guidance"),
            "items": lang_entry.get("items", []),
            "source_title": data.get("source_title", "National Disaster Management Authority (NDMA)"),
            "source_url": data.get("source_url", "https://ndma.gov.in"),
            "retrieved_on": data.get("retrieved_on", "2026-11-17"),
            "reviewed": data.get("reviewed", False),
            "reviewed_by": data.get("reviewed_by", "unreviewed"),
            "style": "guidance-card",  # Neutral styling with dashed border per docs/ui-spec.md
        }
        return [card]

    @staticmethod
    def is_evacuation_query(text: str) -> bool:
        """Determines if query asks whether to evacuate or stay."""
        return any(pattern.search(text) for pattern in EVACUATION_PATTERNS)

    @staticmethod
    def get_evacuation_redirect(language: str = "en") -> dict[str, Any]:
        """Provides direct safety redirection to official disaster authorities and helpline."""
        if language == "hi":
            text = (
                "WeatherGPT व्यक्तिगत रूप से घर खाली करने या रुकने (इवैक्युएशन) का निर्देश नहीं दे सकता। "
                "कृपया अपने जिला आपदा प्रबंधन प्राधिकरण (DDMA), स्थानीय पुलिस या राज्य आपदा प्रबंधन प्राधिकरण द्वारा जारी "
                "आधिकारिक आदेशों का तत्काल पालन करें। किसी भी आपातकालीन स्थिति में राष्ट्रीय आपदा हेल्पलाइन 1070/1077 "
                "या आपातकालीन नंबर 112 पर तुरंत संपर्क करें।"
            )
            headline = "आधिकारिक आपदा निर्देश का पालन करें"
            source = "राष्ट्रीय आपदा प्रबंधन प्राधिकरण (NDMA) एवं स्थानीय प्रशासन"
        else:
            text = (
                "WeatherGPT cannot give personal evacuation instructions or tell you whether to evacuate or stay. "
                "Please immediately follow official evacuation advisories and directives issued by your District Disaster "
                "Management Authority (DDMA), State Disaster Management Authority (SDMA), or local police. "
                "For emergency disaster assistance, dial the Disaster Helpline at 1070 / 1077 or Emergency Services at 112."
            )
            headline = "Follow Official Disaster Directives"
            source = "National Disaster Management Authority (NDMA) & Local Authorities"

        return {
            "text": text,
            "headline": headline,
            "source_line": source,
            "action": "redirect_to_authorities",
            "helplines": ["112", "1077", "1070"],
        }

    @staticmethod
    def is_pesticide_dose_query(text: str) -> bool:
        """Determines if query asks for chemical pesticide dosages."""
        return any(pattern.search(text) for pattern in PESTICIDE_PATTERNS)

    @staticmethod
    def get_pesticide_redirect(language: str = "en") -> dict[str, Any]:
        """Provides safety refusal and redirection for agricultural pesticide dosage requests."""
        if language == "hi":
            text = (
                "WeatherGPT कीटनाशक की मात्रा या रासायनिक दवाओं की खुराक की सिफारिश नहीं करता है। "
                "कीटनाशक की सुरक्षित और सटीक मात्रा फसल की अवस्था, कीट के प्रकोप और स्थानीय कृषि-जलवायु पर निर्भर करती है। "
                "कृपया अनुमोदित मात्रा के लिए अपने नजदीकी कृषि विज्ञान केंद्र (KVK), राज्य कृषि विश्वविद्यालय, "
                "या किसान कॉल सेंटर के टोल-फ्री नंबर 1800-180-1551 पर विशेषज्ञ से संपर्क करें।"
            )
            headline = "कीटनाशक खुराक सलाह उपलब्ध नहीं है"
            source = "कृषि एवं किसान कल्याण मंत्रालय (ICAR / KVK)"
        else:
            text = (
                "WeatherGPT never prescribes chemical pesticide dosages or spray quantities. "
                "Safe pesticide dosages depend strictly on crop growth stage, pest severity, and local agro-climatic conditions. "
                "Please consult your local Krishi Vigyan Kendra (KVK), state agricultural university, or call the "
                "Kisan Call Centre toll-free at 1800-180-1551 for approved expert prescriptions."
            )
            headline = "Pesticide Dosages Not Provided"
            source = "Ministry of Agriculture & Farmers Welfare (ICAR / KVK)"

        return {
            "text": text,
            "headline": headline,
            "source_line": source,
            "action": "redirect_to_kvk",
            "helplines": ["1800-180-1551"],
        }
