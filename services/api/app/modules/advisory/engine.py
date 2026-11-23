from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
import yaml

from services.api.app.modules.advisory.agromet import AgrometAdapter
from services.api.app.modules.advisory.marine import MarineAdapter
from services.api.app.modules.alerts.engine import AlertEngine

logger = structlog.get_logger()

ROOT = Path(__file__).resolve().parents[5]
GUIDANCE_DIR = ROOT / "seeds" / "guidance"

EVACUATION_PATTERNS = [
    re.compile(r"\b(?:should\s+.*evacuate|evacuate\s+or\s+stay|must\s+.*leave|need\s+to\s+evacuate|shall\s+.*evacuate|evacuate\s+our\b|evacuate)\b", re.IGNORECASE),
    re.compile(r"(?:(?:घर|गांव|गाव|গ্রাম|గ్రామ|கிராம|ଗାଁ).*(?:खाली|छोड़|निकल|सोड|छेড়ে|ఖాళీ|காலி|ଛାଡ଼ି))|(?:पलायन|इवैक्युएट|सुरक्षित\s*(?:स्थान|ठिकाणी)|घर\s*खाली|गांव\s*खाली)", re.IGNORECASE),
]

PESTICIDE_PATTERNS = [
    re.compile(r"\b(?:(?:pesticide|insecticide|fungicide|chemical|spray)\s+dos(?:e|age)|dos(?:e|age)\s+of\s+(?:chemical\s+)?(?:pesticide|insecticide|fungicide|spray)|how\s+much\s+(?:pesticide|spray|insecticide|fungicide))\b", re.IGNORECASE),
    re.compile(r"(?:कीटनाशक|কীটনাশক|कीटकनाशक|పురుగుమందు|பூச்சிக்கொல்லி|କୀଟନାଶକ).*(?:मात्रा|खुराक|डोज|छिड़काव|মাত্রা|प्रमाण|మోతాదు|அளவு|ମାତ୍ରା|dose|dosage)|(?:मात्रा|खुराक|डोज|छिड़काव|মাত্রা|प्रमाण|మోతాదు|அளவு|ମାତ୍ରା|dose|dosage).*(?:कीटनाशक|কীটনাশক|कीटकनाशक|పురుగుమందు|பூச்சிக்கொல்லி|କୀଟନାଶକ)", re.IGNORECASE),
]


class AdvisoryEngine:
    """Advisory Engine for official NDMA/IMD heat and cold wave guidance, with safety redirects."""

    def __init__(
        self,
        alert_engine: AlertEngine | None = None,
        agromet_adapter: AgrometAdapter | None = None,
        marine_adapter: MarineAdapter | None = None,
    ) -> None:
        self.alert_engine = alert_engine or AlertEngine()
        self.agromet_adapter = agromet_adapter or AgrometAdapter()
        self.marine_adapter = marine_adapter or MarineAdapter()
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
        crop: str = "wheat",
        stage: str = "sowing",
    ) -> list[dict[str, Any]]:
        """Returns official guidance cards.

        Cards appear ONLY when official warnings apply for heat/cold.
        Agro and marine domains return specialized advisory cards.
        """
        # Handle agro domain
        if "agro" in domain.lower() or "farm" in domain.lower():
            agro_res = await self.agromet_adapter.get_agromet_advisory(
                district=place_id,
                crop=crop,
                stage=stage,
                language=language,
            )
            if agro_res.get("status") == "unavailable":
                return []
            card = {
                "id": f"agromet_{place_id}_{crop}_{stage}_{language}",
                "hazard": "agromet",
                "domain": "agro",
                "place_id": place_id,
                "title": f"Agromet Advisory: {agro_res.get('crop_display', crop.title())} ({agro_res.get('stage_display', stage.title())})",
                "items": [agro_res.get("advisory_text", "")] + [f"Action: {a}" for a in agro_res.get("recommended_actions", [])],
                "source_title": agro_res.get("source", "Gramin Krishi Mausam Sewa (GKMS)"),
                "source_url": "https://agromet.imd.gov.in",
                "retrieved_on": agro_res.get("issue_date", "2026-11-17"),
                "reviewed": True,
                "reviewed_by": "ashwin",
                "style": "guidance-card",
                "agromet_data": agro_res,
            }
            return [card]

        # Handle marine domain
        if "marine" in domain.lower() or "sea" in domain.lower() or "coastal" in domain.lower():
            marine_res = await self.marine_adapter.get_marine_bulletin(
                area=place_id,
                language=language,
            )
            if marine_res.get("status") == "unavailable":
                return []
            fw = marine_res.get("fishermen_warning", {})
            card = {
                "id": f"marine_{place_id}_{language}",
                "hazard": "marine",
                "domain": "marine",
                "place_id": place_id,
                "title": f"Coastal Bulletin: {marine_res.get('area_name', place_id.title())}",
                "items": [
                    f"Weather: {marine_res.get('weather', '')}",
                    f"Wind: {marine_res.get('wind', '')}",
                    f"Sea Condition: {marine_res.get('sea_condition', '')}",
                    f"Fishermen Warning: {fw.get('warning_hi' if language == 'hi' else 'warning_en', '')}",
                ],
                "source_title": marine_res.get("source", "Coastal Weather / INCOIS"),
                "source_url": "https://mausam.imd.gov.in",
                "retrieved_on": marine_res.get("issue_time", "2026-11-17"),
                "reviewed": True,
                "reviewed_by": "ashwin",
                "style": "guidance-card",
                "marine_data": marine_res,
            }
            return [card]

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
        translations = {
            "hi": {
                "text": "WeatherGPT व्यक्तिगत रूप से घर खाली करने या रुकने (इवैक्युएशन) का निर्देश नहीं दे सकता। कृपया अपने जिला आपदा प्रबंधन प्राधिकरण (DDMA), स्थानीय पुलिस या राज्य आपदा प्रबंधन प्राधिकरण द्वारा जारी आधिकारिक आदेशों का तत्काल पालन करें। किसी भी आपातकालीन स्थिति में राष्ट्रीय आपदा हेल्पलाइन 1070/1077 या आपातकालीन नंबर 112 पर तुरंत संपर्क करें।",
                "headline": "आधिकारिक आपदा निर्देश का पालन करें",
                "source": "राष्ट्रीय आपदा प्रबंधन प्राधिकरण (NDMA) एवं स्थानीय प्रशासन",
            },
            "bn": {
                "text": "WeatherGPT ব্যক্তিগতভাবে এলাকা ত্যাগ বা থাকার নির্দেশ দিতে পারে না। অনুগ্রহ করে জেলা দুর্যোগ ব্যবস্থাপনা কর্তৃপক্ষ (DDMA) বা স্থানীয় প্রশাসনের সরকারি নির্দেশ অবিলম্বে মেনে চলুন। জরুরি সহায়তার জন্য হেল্পলাইন ১০৭০ / ১০৭৭ বা ১১২ নম্বরে যোগাযোগ করুন।",
                "headline": "সরকারি দুর্যোগ নির্দেশিকা অনুসরণ করুন",
                "source": "জাতীয় দুর্যোগ ব্যবস্থাপনা কর্তৃপক্ষ (NDMA)",
            },
            "mr": {
                "text": "WeatherGPT वैयक्तिकरित्या स्थलांतर करण्याचा किंवा थांबण्याचा सल्ला देऊ शकत नाही. कृपया जिल्हा आपत्ती व्यवस्थापन प्राधिकरण (DDMA) किंवा स्थानिक प्रशासनाच्या अधिकृत सूचनांचे पालन करा. आपत्कालीन मदतीसाठी १०७० / १०७७ किंवा ११२ वर संपर्क साधा.",
                "headline": "अधिकृत आपत्ती सूचनांचे पालन करा",
                "source": "राष्ट्रीय आपत्ती व्यवस्थापन प्राधिकरण (NDMA)",
            },
            "te": {
                "text": "WeatherGPT వ్యక్తిగతంగా తరలింపు ఆదేశాలను ఇవ్వదు. దయచేసి జిల్లా విపత్తు నిర్వహణ ప్రాధికార సంస్థ (DDMA) లేదా స్థానిక అధికారుల ఆదేశాలను పాటించండి. అత్యవసర సహాయం కోసం 1070 / 1077 లేదా 112 నంబర్లకు సంప్రదించండి.",
                "headline": "అధికారిక విపత్తు ఆదేశాలను పాటించండి",
                "source": "జాతీయ విపత్తు నిర్వహణ అథారిటీ (NDMA)",
            },
            "ta": {
                "text": "WeatherGPT தனிப்பட்ட முறையில் வெளியேறும் வழிமுறைகளை வழங்க முடியாது. மாவட்ட பேரிடர் மேலாண்மை ஆணையம் (DDMA) அல்லது உள்ளூர் அதிகாரிகளின் அதிகாரப்பூர்வ உத்தரவுகளை உடனடியாகப் பின்பற்றவும். அவசர உதவிக்கு 1070 / 1077 அல்லது 112 ஐத் தொடர்பு கொள்ளவும்.",
                "headline": "அதிகாரப்பூர்வ பேரிடர் வழிகாட்டுதல்களைப் பின்பற்றவும்",
                "source": "தேசிய பேரிடர் மேலாண்மை ஆணையம் (NDMA)",
            },
            "or": {
                "text": "WeatherGPT ବ୍ୟକ୍ତିଗତ ଭାବେ ସ୍ଥାନ ଛାଡ଼ିବା କିମ୍ବା ରହିବା ପାଇଁ ନିର୍ଦ୍ଦେଶ ଦେଇପାରିବ ନାହିଁ। ଦୟାକରି ଜିଲ୍ଲା ବିପର୍ଯ୍ୟୟ ପରିଚାଳନା ପ୍ରାଧିକରଣ (DDMA) କିମ୍ବା ସ୍ଥାନୀୟ ପ୍ରଶାସନର ସରକାରୀ ନିର୍ଦ୍ଦେଶ ପାଳନ କରନ୍ତୁ। ଜରୁରୀ ସହାୟତା ପାଇଁ ୧୦୭୦ / ୧୦୭୭ କିମ୍ବା ୧୧୨ କୁ ଯୋଗାଯୋଗ କରନ୍ତୁ।",
                "headline": "ସରକାରୀ ବିପର୍ଯ୍ୟୟ ନିର୍ଦ୍ଦେଶାବଳୀ ଅନୁସରଣ କରନ୍ତୁ",
                "source": "ଜାତୀୟ ବିପର୍ଯ୍ୟୟ ପରିଚାଳନା ପ୍ରାଧିକରଣ (NDMA)",
            },
        }

        entry = translations.get(language, {
            "text": (
                "WeatherGPT cannot give personal relocation directives or instruct residents to leave or stay. "
                "Please immediately follow official safety directives and orders issued by your District Disaster "
                "Management Authority (DDMA), State Disaster Management Authority (SDMA), or local police. "
                "For emergency disaster assistance, dial the Disaster Helpline at 1070 / 1077 or Emergency Services at 112."
            ),
            "headline": "Follow Official Disaster Directives",
            "source": "National Disaster Management Authority (NDMA) & Local Authorities",
        })

        return {
            "text": entry["text"],
            "headline": entry["headline"],
            "source_line": entry["source"],
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
        translations = {
            "hi": {
                "text": "WeatherGPT कीटनाशक की मात्रा या रासायनिक दवाओं की खुराक की सिफारिश नहीं करता है। कीटनाशक की सुरक्षित और सटीक मात्रा फसल की अवस्था, कीट के प्रकोप और स्थानीय कृषि-जलवायु पर निर्भर करती है। कृपया अनुमोदित मात्रा के लिए अपने नजदीकी कृषि विज्ञान केंद्र (KVK), राज्य कृषि विश्वविद्यालय, या किसान कॉल सेंटर के टोल-फ्री नंबर 1800-180-1551 पर विशेषज्ञ से संपर्क करें।",
                "headline": "कीटनाशक खुराक सलाह उपलब्ध नहीं है",
                "source": "कृषि एवं किसान कल्याण मंत्रालय (ICAR / KVK)",
            },
            "bn": {
                "text": "WeatherGPT রাসায়নিক কীটনাশকের মাত্রা নির্ধারণ করে না। সঠিক মাত্রার জন্য অনুগ্রহ করে নিকটস্থ কৃষি বিজ্ঞান কেন্দ্র (KVK) বা কিষাণ কল সেন্টার ১৮০০-১৮০-১৫৫১ নম্বরে যোগাযোগ করুন।",
                "headline": "কীটনাশকের মাত্রা পরামর্শ সমর্থিত নয়",
                "source": "কৃষি ও কৃষক কল্যাণ মন্ত্রক (ICAR / KVK)",
            },
            "mr": {
                "text": "WeatherGPT रासायनिक कीटकनाशकांचे प्रमाण सुचवत नाही. योग्य मार्गदर्शनासाठी कृपया नजीकच्या कृषी विज्ञान केंद्र (KVK) किंवा किसान कॉल सेंटर १८००-१८०-१५५१ वर संपर्क साधा.",
                "headline": "कीटकनाशक प्रमाण सल्ला उपलब्ध नाही",
                "source": "कृषी व शेतकरी कल्याण मंत्रालय (ICAR / KVK)",
            },
            "te": {
                "text": "WeatherGPT రసాయన పురుగుమందుల మోతాదులను సూచించదు. సరైన సలహా కోసం దయచేసి సమీపంలోని కృషి విజ్ఞాన కేంద్రం (KVK) లేదా కిసాన్ కాల్ సెంటర్ 1800-180-1551 కు సంప్రదించండి.",
                "headline": "పురుగుమందుల మోతాదు సలహా అందుబాటులో లేదు",
                "source": "వ్యవసాయ మంత్రిత్వ శాఖ (ICAR / KVK)",
            },
            "ta": {
                "text": "WeatherGPT ரசாயன பூச்சிக்கொல்லி அளவுகளை பரிந்துரைக்காது. பாதுகாப்பான பரிந்துரைகளுக்கு உங்கள் அருகிலுள்ள வேளாண் அறிவியல் மையம் (KVK) அல்லது கிசான் கால் சென்டர் 1800-180-1551 ஐத் தொடர்பு கொள்ளவும்.",
                "headline": "பூச்சிக்கொல்லி அளவு ஆலோசனை வழங்கப்படவில்லை",
                "source": "வேளாண்மை மற்றும் விவசாயிகள் நல அமைச்சகம் (ICAR / KVK)",
            },
            "or": {
                "text": "WeatherGPT ରାସାୟନିକ କୀଟନାଶକର ମାତ୍ରା ସୁପାରିଶ କରେ ନାହିଁ। ସଠିକ୍ ପରାମର୍ଶ ପାଇଁ ନିକଟସ୍ଥ କୃଷି ବିଜ୍ଞାନ କେନ୍ଦ୍ର (KVK) କିମ୍ବା କିଷାନ କଲ୍ ସେଣ୍ଟର ୧୮୦୦-୧୮୦-୧୫୫୧ ରେ ଯୋଗାଯୋଗ କରନ୍ତୁ।",
                "headline": "କୀଟନାଶକ ମାତ୍ରା ପରାମର୍ଶ ଉପଲବ୍ଧ ନାହିଁ",
                "source": "କୃଷି ଓ କୃଷକ କଲ୍ୟାଣ ମନ୍ତ୍ରଣାଳୟ (ICAR / KVK)",
            },
        }

        entry = translations.get(language, {
            "text": (
                "WeatherGPT never prescribes chemical pesticide dosages or spray quantities. "
                "Safe pesticide dosages depend strictly on crop growth stage, pest severity, and local agro-climatic conditions. "
                "Please consult your local Krishi Vigyan Kendra (KVK), state agricultural university, or call the "
                "Kisan Call Centre toll-free at 1800-180-1551 for approved expert prescriptions."
            ),
            "headline": "Pesticide Dosages Not Provided",
            "source": "Ministry of Agriculture & Farmers Welfare (ICAR / KVK)",
        })

        return {
            "text": entry["text"],
            "headline": entry["headline"],
            "source_line": entry["source"],
            "action": "redirect_to_kvk",
            "helplines": ["1800-180-1551"],
        }
