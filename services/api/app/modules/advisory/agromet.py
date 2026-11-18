from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog

from services.api.app.config import Settings

logger = structlog.get_logger()

ROOT = Path(__file__).resolve().parents[5]
FIXTURES_DIR = ROOT / "eval" / "fixtures" / "imd"

CROP_SYNONYMS = {
    "wheat": "wheat",
    "gehu": "wheat",
    "gehun": "wheat",
    "गेहूं": "wheat",
    "गहू": "wheat",
    "গম": "wheat",
    "గోధుమ": "wheat",
    "கோதுமை": "wheat",
    "rice": "rice",
    "paddy": "rice",
    "dhan": "rice",
    "धान": "rice",
    "चावल": "rice",
    "भात": "rice",
    "ধান": "rice",
    "వరి": "rice",
    "அரிசி": "rice",
    "நெல்": "rice",
}

STAGE_SYNONYMS = {
    "sowing": "sowing",
    "seedling": "sowing",
    "बुवाई": "sowing",
    "अंकुरण": "sowing",
    "nursery": "nursery",
    "नर्सरी": "nursery",
    "transplanting": "transplanting",
    "रोपाई": "transplanting",
    "cri": "crown_root_initiation",
    "crown_root_initiation": "crown_root_initiation",
    "crown root": "crown_root_initiation",
    "शीर्ष जड़": "crown_root_initiation",
    "vegetative": "vegetative",
    "tillering": "vegetative",
    "वानस्पतिक": "vegetative",
    "कल्ले": "vegetative",
    "flowering": "flowering",
    "heading": "flowering",
    "panicle": "flowering",
    "panicle_initiation": "flowering",
    "फूल": "flowering",
    "बाली": "flowering",
    "grain_filling": "grain_filling",
    "milking": "grain_filling",
    "दूधिया": "grain_filling",
    "दाना भराव": "grain_filling",
    "maturity": "maturity",
    "harvesting": "maturity",
    "harvest": "maturity",
    "कटाई": "maturity",
    "परिपक्वता": "maturity",
}


class AgrometAdapter:
    """Adapter for IMD Gramin Krishi Mausam Sewa (GKMS) Agromet Advisory Bulletins.

    Follows ADR 0007: stays contract-first with documented-sample fixtures until the IMD key arrives.
    Strictly refuses chemical pesticide dosages and redirects to KVK / Kisan Call Centre.
    """

    def __init__(
        self,
        fixture_path: Path | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.fixture_path = fixture_path or (FIXTURES_DIR / "agromet_advisory_sample.json")
        self.settings = settings or Settings()
        self._bulletin_cache: dict[str, Any] | None = None
        self._load_fixtures()

    def _load_fixtures(self) -> None:
        if self.fixture_path.exists():
            try:
                with self.fixture_path.open("r", encoding="utf-8") as f:
                    self._bulletin_cache = json.load(f)
            except Exception as e:
                logger.warning("agromet_fixture_load_failed", path=str(self.fixture_path), error=str(e))
                self._bulletin_cache = None

    def normalize_crop(self, crop_input: str) -> str:
        clean = crop_input.strip().lower()
        return CROP_SYNONYMS.get(clean, "wheat")

    def normalize_stage(self, stage_input: str) -> str:
        clean = stage_input.strip().lower()
        for k, v in STAGE_SYNONYMS.items():
            if k in clean:
                return v
        return "vegetative"

    def normalize_district(self, district_input: str) -> str:
        clean = district_input.strip().lower().replace("district", "").strip()
        # Direct aliases
        if "ludhiana" in clean:
            return "ludhiana"
        if "karnal" in clean:
            return "karnal"
        if "varanasi" in clean or "banaras" in clean or "kashi" in clean:
            return "varanasi"
        if "burdwan" in clean or "bardhaman" in clean:
            return "burdwan"
        return clean

    async def get_agromet_advisory(
        self,
        district: str,
        crop: str = "wheat",
        stage: str = "sowing",
        language: str = "en",
        query_text: str = "",
    ) -> dict[str, Any]:
        """Fetches agromet advisory summary for the specified district, crop and growth stage."""
        # 1. Strict safety check: Never prescribe chemical pesticide dosages
        from services.api.app.modules.advisory.engine import AdvisoryEngine

        combined_text = f"{stage} {query_text}".strip()
        if AdvisoryEngine.is_pesticide_dose_query(combined_text):
            logger.info("agromet_pesticide_query_refused", query=combined_text)
            redirect = AdvisoryEngine.get_pesticide_redirect(language)
            return {
                "status": "refused_pesticide_dose",
                "pesticide_refusal": True,
                "district": district,
                "crop": crop,
                "stage": stage,
                "redirect": redirect,
                "headline": redirect["headline"],
                "source": redirect["source_line"],
                "helplines": redirect["helplines"],
                "message": redirect["text"],
            }

        norm_crop = self.normalize_crop(crop)
        norm_stage = self.normalize_stage(stage)
        norm_dist = self.normalize_district(district)

        if not self._bulletin_cache:
            self._load_fixtures()

        bulletin = self._bulletin_cache or {}
        districts = bulletin.get("districts", {})

        # Find matching district or fall back gracefully to first available district
        dist_data = districts.get(norm_dist)
        if not dist_data:
            # Fall back to ludhiana for wheat, burdwan for rice if not found
            fallback_key = "ludhiana" if norm_crop == "wheat" else "burdwan"
            dist_data = districts.get(fallback_key, next(iter(districts.values())) if districts else {})

        crop_data = dist_data.get("crops", {}).get(norm_crop)
        if not crop_data:
            # If specified crop not in district, take available crop
            crops_avail = dist_data.get("crops", {})
            norm_crop = next(iter(crops_avail.keys())) if crops_avail else norm_crop
            crop_data = crops_avail.get(norm_crop, {})

        stages_dict = crop_data.get("stages", {})
        stage_info = stages_dict.get(norm_stage)
        if not stage_info:
            # Fall back to first stage in list
            stage_info = next(iter(stages_dict.values())) if stages_dict else {}

        # Select localized text
        is_hi = language == "hi"
        crop_display = crop_data.get("crop_name_hi" if is_hi else "crop_name", norm_crop.title())
        stage_display = stage_info.get("stage_name_hi" if is_hi else "stage_name", norm_stage.title())
        advisory_text = stage_info.get("advisory_hi" if is_hi else "advisory_en", "")

        organization = bulletin.get(
            "organization",
            "Gramin Krishi Mausam Sewa (GKMS), India Meteorological Department (IMD) in collaboration with ICAR",
        )
        issue_date = bulletin.get("issue_date", "2026-11-17")
        valid_until = bulletin.get("valid_until", "2026-11-21")
        provenance = bulletin.get("_provenance", "documented-sample")

        safety_note = (
            "नोट: यह सलाह केवल मौसम आधारित कृषि मार्गदर्शन हेतु है। किसी भी रासायनिक कीटनाशक की मात्रा के लिए नजदीकी KVK या 1800-180-1551 पर संपर्क करें।"
            if is_hi
            else "Note: Weather-based agro-advisory only. For chemical pesticide dosage, contact local KVK or Kisan Call Centre 1800-180-1551."
        )

        return {
            "status": "success",
            "district": dist_data.get("district_name", district.title()),
            "state": dist_data.get("state", "India"),
            "crop": norm_crop,
            "crop_display": crop_display,
            "stage": norm_stage,
            "stage_display": stage_display,
            "advisory_text": advisory_text,
            "recommended_actions": stage_info.get("recommended_actions", []),
            "source": organization,
            "authority_tier": 2,
            "issue_date": issue_date,
            "valid_until": valid_until,
            "safety_note": safety_note,
            "provenance": provenance,
            "imd_key_status": "live" if self.settings.imd_enabled else "pending_key_contract_fixture",
        }
