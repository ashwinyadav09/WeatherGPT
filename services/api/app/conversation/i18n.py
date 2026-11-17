from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SEEDS_DIR = ROOT / "seeds" / "i18n"

# Common Romanized Hindi words for code-mixed / Hinglish detection
HINGLISH_WORDS = {
    "kya",
    "barish",
    "baarish",
    "barsaat",
    "hogi",
    "hoga",
    "honge",
    "mausam",
    "kaisa",
    "kaisi",
    "rahega",
    "rahegi",
    "kal",
    "aaj",
    "parso",
    "parson",
    "kitni",
    "kitna",
    "pani",
    "chata",
    "chhaata",
    "chhate",
    "garmi",
    "sardi",
    "thand",
    "badal",
    "bijli",
    "hawa",
    "tez",
    "tezz",
    "aandhi",
    "tufan",
    "toofan",
}


@dataclass
class GlossaryCheckResult:
    is_valid: bool
    errors: list[str]


def detect_language(text: str) -> str:
    """Detect whether text is Hindi (Devanagari or Hinglish/code-mixed) or English."""
    # Check for Devanagari Unicode range
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    # Check for Romanized Hindi / Hinglish tokens
    words = set(re.findall(r"\b[a-zA-Z]+\b", text.lower()))
    if words.intersection(HINGLISH_WORDS):
        return "hi"

    return "en"


def get_hindi_probability_phrase(probability_pct: float) -> str:
    """Map rain probability percentage to standard Hindi phrase per seeds/i18n/uncertainty.hi.yaml."""
    if probability_pct <= 10.0:
        return "बहुत कम संभावना"
    elif probability_pct <= 30.0:
        return "कम संभावना"
    elif probability_pct <= 60.0:
        return "संभावना है"
    elif probability_pct <= 80.0:
        return "काफ़ी संभावना"
    else:
        return "बहुत अधिक संभावना"


def get_hindi_rainfall_phrase(rainfall_mm: float) -> str:
    """Map rainfall amount to IMD-aligned Hindi category per seeds/i18n/uncertainty.hi.yaml."""
    if rainfall_mm < 0.1:
        return "मौसम शुष्क रहेगा (बारिश नहीं)"
    elif rainfall_mm <= 2.4:
        return "बहुत हल्की बारिश"
    elif rainfall_mm <= 15.5:
        return "हल्की बारिश"
    elif rainfall_mm <= 64.4:
        return "मध्यम बारिश"
    elif rainfall_mm <= 115.5:
        return "भारी बारिश"
    elif rainfall_mm <= 204.4:
        return "बहुत भारी बारिश"
    else:
        return "अत्यंत भारी बारिश"


FORBIDDEN_HINDI_PATTERNS = [
    r"गारंटी",
    r"पक्की गारंटी",
    r"निकासी जरूरी",
    r"निकासी आवश्यक",
    r"तुरंत खाली करें",
    r"खाली करने का आदेश",
]


def check_hindi_glossary(text: str) -> GlossaryCheckResult:
    """Verify that generated Hindi text adheres to project glossary rules and contains no forbidden phrases."""
    errors: list[str] = []

    for pat in FORBIDDEN_HINDI_PATTERNS:
        if re.search(pat, text):
            errors.append(f"Forbidden phrase pattern matched: '{pat}'")

    return GlossaryCheckResult(
        is_valid=len(errors) == 0,
        errors=errors,
    )


def normalize_for_speech_hi(text: str) -> str:
    """Normalize numerical and unit representations into spoken Hindi forms for TTS."""
    # Degrees Celsius
    s = re.sub(r"\bdegC\b|°C|celsius", "डिग्री सेल्सियस", text, flags=re.IGNORECASE)
    # Millimeters
    s = re.sub(r"\bmm\b|मिमी", "मिलीमीटर", s, flags=re.IGNORECASE)
    # Kilometers per hour
    s = re.sub(r"\bkm/h\b|\bkmh\b|किमी/घंटा|किमी/घं", "किलोमीटर प्रति घंटा", s, flags=re.IGNORECASE)
    # Percent
    s = re.sub(r"%", " प्रतिशत", s)
    return s
