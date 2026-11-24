"""Multilingual slot parser for user weather queries (Ticket R12).

Extracts:
1. Place: gazetteer fuzzy matching + alias lookup
2. Date range: rule-based multilingual regex parser across English, Hindi, Bengali, Marathi, Telugu, Tamil, Odia
3. Crop: per-language agricultural lexicon
4. Hazard: per-language weather hazard lexicon
"""
from __future__ import annotations

import re
from typing import Any

# Multilingual crop lexicon: normalized name -> canonical English name
CROP_LEXICON: dict[str, str] = {
    # English
    "wheat": "wheat",
    "rice": "rice",
    "paddy": "rice",
    "sugarcane": "sugarcane",
    "cotton": "cotton",
    "mustard": "mustard",
    "maize": "maize",
    "corn": "maize",
    "soybean": "soybean",
    "groundnut": "groundnut",
    "peanut": "groundnut",
    "gram": "chickpea",
    "chickpea": "chickpea",
    "potato": "potato",
    "onion": "onion",
    "tomato": "tomato",
    # Hindi
    "गेहूं": "wheat",
    "धान": "rice",
    "चावल": "rice",
    "गन्ना": "sugarcane",
    "कपास": "cotton",
    "सरसों": "mustard",
    "मक्का": "maize",
    "सोयाबीन": "soybean",
    "मूंगफली": "groundnut",
    "चना": "chickpea",
    "आलू": "potato",
    "प्याज": "onion",
    "टमाटर": "tomato",
    # Bengali
    "গম": "wheat",
    "ধান": "rice",
    "চাল": "rice",
    "আখ": "sugarcane",
    "তুলা": "cotton",
    "সরিষা": "mustard",
    "ভুট্টা": "maize",
    "আলু": "potato",
    # Marathi
    "गहू": "wheat",
    "गव्हाला": "wheat",
    "गव्हाच्या": "wheat",
    "भात": "rice",
    "भाताच्या": "rice",
    "ऊस": "sugarcane",
    "उसाच्या": "sugarcane",
    "उसा": "sugarcane",
    "कापूस": "cotton",
    "कापसाच्या": "cotton",
    "मोहरी": "mustard",
    "मका": "maize",
    "भुईमूग": "groundnut",
    "कांदा": "onion",
    # Telugu
    "గోధుమ": "wheat",
    "వరి": "rice",
    "చెరకు": "sugarcane",
    "పత్తి": "cotton",
    "ఆవాలు": "mustard",
    "మొక్కజొన్న": "maize",
    "వేరుశనగ": "groundnut",
    # Tamil
    "கோதுமை": "wheat",
    "நெல்": "rice",
    "கரும்பு": "sugarcane",
    "பருத்தி": "cotton",
    "கடுகு": "mustard",
    "மக்காச்சோளம்": "maize",
    "வேர்க்கடலை": "groundnut",
    # Odia
    "ଗହମ": "wheat",
    "ଧାନ": "rice",
    "ଆଖୁ": "sugarcane",
    "କପା": "cotton",
    "ସୋରିଷ": "mustard",
    "ମକା": "maize",
}

# Multilingual hazard lexicon: normalized term -> canonical English name
HAZARD_LEXICON: dict[str, str] = {
    # English
    "heatwave": "heatwave",
    "heat wave": "heatwave",
    "cold wave": "coldwave",
    "coldwave": "coldwave",
    "rain": "rain",
    "heavy rain": "heavy_rain",
    "rainfall": "rain",
    "cyclone": "cyclone",
    "flood": "flood",
    "thunderstorm": "thunderstorm",
    "lightning": "lightning",
    "fog": "fog",
    "frost": "frost",
    "hail": "hail",
    "hailstorm": "hail",
    # Hindi
    "लू": "heatwave",
    "गर्मी की लहर": "heatwave",
    "शीतलहर": "coldwave",
    "ठंड": "coldwave",
    "बारिश": "rain",
    "भारी बारिश": "heavy_rain",
    "वर्षा": "rain",
    "चक्रवात": "cyclone",
    "तूफान": "cyclone",
    "बाढ़": "flood",
    "आंधी": "thunderstorm",
    "बिजली": "lightning",
    "कोहरा": "fog",
    "पाला": "frost",
    "ओलावृष्टि": "hail",
    "ओले": "hail",
    # Bengali
    "তাপপ্রবাহ": "heatwave",
    "শৈত্যপ্রবাহ": "coldwave",
    "বৃষ্টি": "rain",
    "ভারী বৃষ্টি": "heavy_rain",
    "ঘূর্ণিঝড়": "cyclone",
    "বন্যা": "flood",
    "বজ্রপাত": "lightning",
    "কুয়াশা": "fog",
    # Marathi
    "उष्णतेची लाट": "heatwave",
    "थंडीची लाट": "coldwave",
    "पाऊस": "rain",
    "मुसळधार पाऊस": "heavy_rain",
    "चक्रीवादळ": "cyclone",
    "पूर": "flood",
    "विजा": "lightning",
    "धुके": "fog",
    # Telugu
    "వడగాల్పులు": "heatwave",
    "శీతల గాలులు": "coldwave",
    "వర్షం": "rain",
    "భారీ వర్షం": "heavy_rain",
    "తుఫాను": "cyclone",
    "వరద": "flood",
    "మెరుపులు": "lightning",
    "పొగమంచు": "fog",
    # Tamil
    "வெப்ப அலை": "heatwave",
    "குளிர் அலை": "coldwave",
    "மழை": "rain",
    "கனமழை": "heavy_rain",
    "புயல்": "cyclone",
    "வெள்ளம்": "flood",
    "மின்னல்": "lightning",
    "பனிமூட்டம்": "fog",
    # Odia
    "ଗ୍ରୀଷ୍ମ ପ୍ରବାହ": "heatwave",
    "ଶୀତ ଲହରୀ": "coldwave",
    "ବର୍ଷା": "rain",
    "ପ୍ରବଳ ବର୍ଷା": "heavy_rain",
    "ବାତ୍ୟା": "cyclone",
    "ବନ୍ୟା": "flood",
    "ବଜ୍ରପାତ": "lightning",
    "କୁହୁଡ଼ି": "fog",
}

# Multilingual date/time regex patterns: (regex pattern, canonical English label)
DATE_PATTERNS: list[tuple[re.Pattern, str]] = [
    # English
    (re.compile(r"\b(today|tonight|this\s*morning|right\s*now)\b", re.IGNORECASE), "today"),
    (re.compile(r"\b(tomorrow|tmrw)\b", re.IGNORECASE), "tomorrow"),
    (re.compile(r"\b(day\s*after\s*tomorrow)\b", re.IGNORECASE), "day_after_tomorrow"),
    (re.compile(r"\b(this\s*weekend|weekend)\b", re.IGNORECASE), "this_weekend"),
    (re.compile(r"\b(next\s*week)\b", re.IGNORECASE), "next_week"),
    (re.compile(r"\b(7\s*days?|next\s*7\s*days?)\b", re.IGNORECASE), "next_7_days"),
    (re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE), "named_day"),
    # Hindi & Hinglish
    (re.compile(r"\b(आज|aaj)\b", re.IGNORECASE), "today"),
    (re.compile(r"\b(कल|kal)\b", re.IGNORECASE), "tomorrow"),
    (re.compile(r"\b(परसों|parson|parso)\b", re.IGNORECASE), "day_after_tomorrow"),
    (re.compile(r"\b(इस\s*हफ्ते|is\s*hafte)\b", re.IGNORECASE), "this_week"),
    (re.compile(r"\b(अगले\s*हफ्ते|agle\s*hafte)\b", re.IGNORECASE), "next_week"),
    (re.compile(r"\b(7\s*दिन|सात\s*दिन)\b", re.IGNORECASE), "next_7_days"),
    # Bengali
    (re.compile(r"(আজ|এখন)"), "today"),
    (re.compile(r"(আগামীকাল|কাল)"), "tomorrow"),
    (re.compile(r"(পরশু)"), "day_after_tomorrow"),
    (re.compile(r"(এই\s*সপ্তাহে)"), "this_week"),
    (re.compile(r"(পরের\s*সপ্তাহে)"), "next_week"),
    # Marathi
    (re.compile(r"(आज)"), "today"),
    (re.compile(r"(उद्या)"), "tomorrow"),
    (re.compile(r"(परवा)"), "day_after_tomorrow"),
    (re.compile(r"(या\s*आठवड्यात)"), "this_week"),
    (re.compile(r"(पुढील\s*आठवड्यात)"), "next_week"),
    # Telugu
    (re.compile(r"(ఈ\s*రోజు|నేడు)"), "today"),
    (re.compile(r"(రేపు)"), "tomorrow"),
    (re.compile(r"(ఎల్లుండి)"), "day_after_tomorrow"),
    (re.compile(r"(ఈ\s*వారం)"), "this_week"),
    (re.compile(r"(వచ్చే\s*వారం)"), "next_week"),
    # Tamil
    (re.compile(r"(இன்று)"), "today"),
    (re.compile(r"(நாளை)"), "tomorrow"),
    (re.compile(r"(நாளை\s*மறுநாள்)"), "day_after_tomorrow"),
    (re.compile(r"(இந்த\s*வாரம்)"), "this_week"),
    (re.compile(r"(அடுத்த\s*வாரம்)"), "next_week"),
    # Odia
    (re.compile(r"(ଆଜି)"), "today"),
    (re.compile(r"(ଆସନ୍ତାକାଲି|କାଲି)"), "tomorrow"),
    (re.compile(r"(ପଅରଦିନ)"), "day_after_tomorrow"),
    (re.compile(r"(ଏହି\s*ସପ୍ତାହ)"), "this_week"),
    (re.compile(r"(ଆସନ୍ତା\s*ସପ୍ତାହ)"), "next_week"),
]

# Major Indian places for fast matching (English, Hindi, Regional aliases)
KNOWN_PLACES: list[tuple[str, str]] = [
    ("delhi", "Delhi"),
    ("दिल्ली", "Delhi"),
    ("দিল্লি", "Delhi"),
    ("ఢిల్లీ", "Delhi"),
    ("டெல்லி", "Delhi"),
    ("ଦିଲ୍ଲୀ", "Delhi"),
    ("new delhi", "Delhi"),
    ("mumbai", "Mumbai"),
    ("मुंबई", "Mumbai"),
    ("মুম্বই", "Mumbai"),
    ("ముంబై", "Mumbai"),
    ("மும்பை", "Mumbai"),
    ("ମୁମ୍ବାଇ", "Mumbai"),
    ("bombay", "Mumbai"),
    ("bengaluru", "Bengaluru"),
    ("bangalore", "Bengaluru"),
    ("बेंगलुरु", "Bengaluru"),
    ("बंगळुरू", "Bengaluru"),
    ("বেঙ্গালুরু", "Bengaluru"),
    ("బెంగళూరు", "Bengaluru"),
    ("பெங்களூரு", "Bengaluru"),
    ("ବେଙ୍ଗାଲୁରୁ", "Bengaluru"),
    ("chennai", "Chennai"),
    ("चेन्नई", "Chennai"),
    ("மட்ராஸ்", "Chennai"),
    ("சென்னை", "Chennai"),
    ("చైన్నై", "Chennai"),
    ("madras", "Chennai"),
    ("kolkata", "Kolkata"),
    ("कोलकाता", "Kolkata"),
    ("কলকাতা", "Kolkata"),
    ("కోల్‌కతా", "Kolkata"),
    ("கொல்கத்தா", "Kolkata"),
    ("calcutta", "Kolkata"),
    ("hyderabad", "Hyderabad"),
    ("हैदराबाद", "Hyderabad"),
    ("హైదరాబాద్", "Hyderabad"),
    ("হায়দ্রাবাদ", "Hyderabad"),
    ("ஹைதராபாத்", "Hyderabad"),
    ("pune", "Pune"),
    ("पुण्यात", "Pune"),
    ("पुण्यातील", "Pune"),
    ("पुणे", "Pune"),
    ("পুনেতে", "Pune"),
    ("পুনে", "Pune"),
    ("పూణేలో", "Pune"),
    ("పూణే", "Pune"),
    ("புனேயில்", "Pune"),
    ("புனே", "Pune"),
    ("கொல்கத்தாவில்", "Kolkata"),
    ("சென்னையில்", "Chennai"),
    ("ஹைதராபாத்தில்", "Hyderabad"),
    ("హైదరాబాద్‌లో", "Hyderabad"),
    ("భూవనేశ్వర్", "Bhubaneswar"),
    ("ଭୁବନେଶ୍ୱରରେ", "Bhubaneswar"),
    ("कोलकाताয়", "Kolkata"),
    ("দিল্লিতে", "Delhi"),
    ("jaipur", "Jaipur"),
    ("जयपुर", "Jaipur"),
    ("জয়পুর", "Jaipur"),
    ("जयपूर", "Jaipur"),
    ("shimla", "Shimla"),
    ("शिमला", "Shimla"),
    ("guwahati", "Guwahati"),
    ("गुवाहाटी", "Guwahati"),
    ("varanasi", "Varanasi"),
    ("वाराणसी", "Varanasi"),
    ("banaras", "Varanasi"),
    ("kashi", "Varanasi"),
    ("lucknow", "Lucknow"),
    ("लखनऊ", "Lucknow"),
    ("patna", "Patna"),
    ("पटना", "Patna"),
    ("nagpur", "Nagpur"),
    ("नागपुर", "Nagpur"),
    ("ahmedabad", "Ahmedabad"),
    ("अहमदाबाद", "Ahmedabad"),
    ("bhopal", "Bhopal"),
    ("भोपाल", "Bhopal"),
    ("ranchi", "Ranchi"),
    ("राँची", "Ranchi"),
    ("bhubaneswar", "Bhubaneswar"),
    ("भुवनेश्वर", "Bhubaneswar"),
    ("ଭୁବନେଶ୍ୱର", "Bhubaneswar"),
    ("odisha", "Odisha"),
    ("ओडिशा", "Odisha"),
    ("punjab", "Punjab"),
    ("पंजाब", "Punjab"),
    ("rajasthan", "Rajasthan"),
    ("राजस्थान", "Rajasthan"),
    ("gujarat", "Gujarat"),
    ("गुजरात", "Gujarat"),
    ("kerala", "Kerala"),
    ("केरल", "Kerala"),
    ("maharashtra", "Maharashtra"),
    ("महाराष्ट्र", "Maharashtra"),
    ("bihar", "Bihar"),
    ("बिहार", "Bihar"),
    ("assam", "Assam"),
    ("असम", "Assam"),
    ("west bengal", "West Bengal"),
    ("पश्चिम बंगाल", "West Bengal"),
]


def extract_slots(text: str) -> dict[str, Any]:
    """Extract place, date_range, crop, and hazard slots from text."""
    slots: dict[str, Any] = {
        "place": None,
        "date_range": None,
        "crop": None,
        "hazard": None,
    }
    low = text.lower()

    # 1. Place extraction (longest match first)
    for token, canonical in sorted(KNOWN_PLACES, key=lambda x: len(x[0]), reverse=True):
        if token.lower() in low or token in text:
            slots["place"] = canonical
            break

    # 2. Date extraction
    for pat, label in DATE_PATTERNS:
        if pat.search(text) or pat.search(low):
            slots["date_range"] = label
            break

    # 3. Crop extraction (longest match first)
    for term, canonical_crop in sorted(CROP_LEXICON.items(), key=lambda x: len(x[0]), reverse=True):
        if term in low or term in text:
            slots["crop"] = canonical_crop
            break

    # 4. Hazard extraction (longest match first)
    for term, canonical_hazard in sorted(HAZARD_LEXICON.items(), key=lambda x: len(x[0]), reverse=True):
        if term in low or term in text:
            slots["hazard"] = canonical_hazard
            break

    return slots
