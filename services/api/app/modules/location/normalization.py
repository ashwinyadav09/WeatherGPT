from __future__ import annotations

import re
import unicodedata

# Common Indian place transliterations and historical names mapping to canonical IDs
CANONICAL_ALIASES: dict[str, str] = {
    # Historical / colloquial English transliterations
    "poona": "pune",
    "puna": "pune",
    "bombay": "mumbai",
    "bambai": "mumbai",
    "bangalore": "bengaluru",
    "bengalooru": "bengaluru",
    "calcutta": "kolkata",
    "kolkatta": "kolkata",
    "madras": "chennai",
    "baroda": "vadodara",
    "banaras": "varanasi",
    "benares": "varanasi",
    "kashi": "varanasi",
    "allahabad": "prayagraj",
    "ilhabad": "prayagraj",
    "gauhati": "guwahati",
    "cochin": "kochi",
    "simla": "shimla",
    "trichy": "tiruchirappalli",
    "ooty": "udhagamandalam",
    "gurgaon": "gurugram",
    "waltair": "visakhapatnam",
    "vizag": "visakhapatnam",
    "bellary": "ballari",
    "mysore": "mysuru",
    "hubli": "hubballi",
    "mangalore": "mangaluru",
    "belgaum": "belagavi",
    "orissa": "odisha",
    "trivandrum": "thiruvananthapuram",
    "pondicherry": "puducherry",
    "calicut": "kozhikode",
    "cawnpore": "kanpur",
    "ahmadabad": "ahmedabad",

    # Hindi / Devanagari transliterations
    "पुना": "pune",
    "पुणे": "pune",
    "पुण्यात": "pune",
    "पुण्यामध्ये": "pune",
    "धुळे": "dhule",
    "धुले": "dhule",
    "धुळ्यात": "dhule",
    "धुळ्यामध्ये": "dhule",
    "अहमदनगर": "ahmednagar",
    "अहमदनगरला": "ahmednagar",
    "अहमदनगरमध्ये": "ahmednagar",
    "अहिल्यानगर": "ahmednagar",
    "बम्बई": "mumbai",
    "मुंबई": "mumbai",
    "बैंगलोर": "bengaluru",
    "बेंगलुरु": "bengaluru",
    "बंगलौर": "bengaluru",
    "कलकत्ता": "kolkata",
    "कोलकाता": "kolkata",
    "मद्रास": "chennai",
    "चेन्नई": "chennai",
    "बड़ौदा": "vadodara",
    "वडोदरा": "vadodara",
    "बनारस": "varanasi",
    "काशी": "varanasi",
    "वाराणसी": "varanasi",
    "इलाहाबाद": "prayagraj",
    "प्रयागराज": "prayagraj",
    "गुवाहाटी": "guwahati",
    "गौहाटी": "guwahati",
    "कोच्चि": "kochi",
    "कोचीन": "kochi",
    "शिमला": "shimla",
    "गुड़गांव": "gurugram",
    "गुरुग्राम": "gurugram",
    "विशाखापट्टनम": "visakhapatnam",
    "वाइज़ैग": "visakhapatnam",
    "मैसूर": "mysuru",
    "मैसुरु": "mysuru",
    "त्रिवेंद्रम": "thiruvananthapuram",
    "तिरुवनंतपुरम": "thiruvananthapuram",

    # Odia transliterations & inflections
    "ଭୁବନେଶ୍ୱର": "bhubaneswar",
    "ଭୁବନେଶ୍ୱରରେ": "bhubaneswar",
    "ପୁରୀ": "puri",
    "ପୁରୀରେ": "puri",
    "କଟକ": "cuttack",
    "କଟକରେ": "cuttack",
}

# Stopwords and query fillers commonly spoken in English, Hindi, and Marathi
STOP_WORDS = {
    # English
    "in", "at", "for", "near", "around", "weather", "forecast", "rain", "temperature",
    "will", "it", "tomorrow", "today", "yesterday", "district", "city", "village",
    "block", "tehsil", "taluk", "taluka", "panchayat", "state", "the", "of", "is",
    # Hindi
    "में", "पर", "के", "का", "की", "मौसम", "पूर्वानुमान", "बारिश", "तापमान", "हवामान",
    "कल", "आज", "जिला", "ज़िला", "शहर", "गाँव", "गांव", "ब्लॉक", "तहसील", "पंचायत",
    "क्या", "होगी", "होगा", "बताओ", "दिखाओ", "कैसा", "रहेगा", "है",
    # Marathi
    "मधील", "मध्ये", "चा", "ची", "चे", "हवामान", "पाऊस", "उद्या", "आज", "तालुका", "गाव",
}


def normalize_text(text: str) -> str:
    """Normalize text removing accents, punctuation and excessive whitespace."""
    if not text:
        return ""
    # Unicode normalize NFC
    text = unicodedata.normalize("NFC", text)
    # Lowercase
    text = text.lower()
    # Replace punctuation with spaces
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)
    return " ".join(text.split())


def extract_potential_place_tokens(query: str) -> list[str]:
    """Extract candidate place words by filtering out conversational stopwords."""
    norm = normalize_text(query)
    words = norm.split()
    cleaned = [w for w in words if w not in STOP_WORDS]
    candidates = []

    # Try full cleaned phrase
    if cleaned:
        candidates.append(" ".join(cleaned))

    # Try 2-grams and 1-grams
    for i in range(len(cleaned)):
        candidates.append(cleaned[i])
        if i + 1 < len(cleaned):
            candidates.append(f"{cleaned[i]} {cleaned[i+1]}")

    return candidates
