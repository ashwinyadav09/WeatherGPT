from __future__ import annotations

import re

# Hindi number words 0 to 100
HINDI_NUMBERS: dict[int, str] = {
    0: "शून्य", 1: "एक", 2: "दो", 3: "तीन", 4: "चार", 5: "पांच",
    6: "छह", 7: "सात", 8: "आठ", 9: "नौ", 10: "दस",
    11: "ग्यारह", 12: "बारह", 13: "तेरह", 14: "चौदह", 15: "पंद्रह",
    16: "सोलह", 17: "सत्रह", 18: "अठारह", 19: "उन्नीस", 20: "बीस",
    21: "इक्कीस", 22: "बाईस", 23: "तेईस", 24: "चौबीस", 25: "पच्चीस",
    26: "छब्बीस", 27: "सत्ताईस", 28: "अट्ठाइस", 29: "उनतीस", 30: "तीस",
    31: "इकत्तीस", 32: "बत्तीस", 33: "तैंतीस", 34: "चौंतीस", 35: "पैंतीस",
    36: "छत्तीस", 37: "सैंतीस", 38: "अड़तीस", 39: "उनतालीस", 40: "चालीस",
    41: "इकतालीस", 42: "बयालीस", 43: "तैंतालीस", 44: "चौवालीस", 45: "पैंतालीस",
    46: "छियालीस", 47: "सैंतालीस", 48: "अड़तालीस", 49: "उनचास", 50: "पचास",
    51: "इक्यावन", 52: "बावन", 53: "तिरपन", 54: "चौवन", 55: "पचपन",
    56: "छप्पन", 57: "सत्तावन", 58: "अट्ठावन", 59: "उनसठ", 60: "साठ",
    61: "इकसठ", 62: "बासठ", 63: "तिरसठ", 64: "चौंसठ", 65: "पैंसठ",
    66: "छियासठ", 67: "सरसठ", 68: "अड़सठ", 69: "उनहत्तर", 70: "सत्तर",
    71: "इकहत्तर", 72: "बहत्तर", 73: "तिहत्तर", 74: "चौहत्तर", 75: "पचहत्तर",
    76: "छिहत्तर", 77: "सतहत्तर", 78: "अठहत्तर", 79: "उनासी", 80: "अस्सी",
    81: "इक्यासी", 82: "बयासी", 83: "तिरासी", 84: "चौरासी", 85: "पचासी",
    86: "छियासी", 87: "सत्तासी", 88: "अट्ठासी", 89: "नवासी", 90: "नब्बे",
    91: "इक्यानवे", 92: "बानवे", 93: "तिरानवे", 94: "चौरानवे", 95: "पंचानवे",
    96: "छियानवे", 97: "सत्तानवे", 98: "अट्ठानवे", 99: "निन्यानवे", 100: "सौ",
}


def number_to_hindi(n: int) -> str:
    """Convert an integer into natural spoken Hindi words."""
    if n in HINDI_NUMBERS:
        return HINDI_NUMBERS[n]
    if n < 0:
        return f"माइनस {number_to_hindi(-n)}"
    if n < 1000:
        hundreds = n // 100
        rem = n % 100
        h_str = f"{HINDI_NUMBERS.get(hundreds, str(hundreds))} सौ"
        return f"{h_str} {number_to_hindi(rem)}" if rem > 0 else h_str
    if n < 100000:
        thousands = n // 1000
        rem = n % 1000
        t_str = f"{HINDI_NUMBERS.get(thousands, str(thousands))} हज़ार"
        return f"{t_str} {number_to_hindi(rem)}" if rem > 0 else t_str
    return str(n)


def normalize_for_tts(text: str, language: str = "hi") -> str:
    """Normalizes weather text, numbers, units, degrees, and times for natural speech synthesis."""
    if not text:
        return ""

    normalized = text

    if language.startswith("hi"):
        # 1. Temperature units: e.g. 32°C, 32 °C, -2°C
        def replace_temp(match: re.Match) -> str:
            val_str = match.group(1)
            try:
                val = int(val_str)
                spoken = number_to_hindi(val)
            except ValueError:
                spoken = val_str
            return f"{spoken} डिग्री सेल्सियस"

        normalized = re.sub(r"(-?\d+)\s*(?:°C|°|डिग्री\s*सेल्शियस|deg\s*C)\b", replace_temp, normalized)

        # 2. Wind speed: e.g. 15 km/h, 15 kmph, 15 किमी/घंटा
        def replace_speed(match: re.Match) -> str:
            val_str = match.group(1)
            try:
                val = int(val_str)
                spoken = number_to_hindi(val)
            except ValueError:
                spoken = val_str
            return f"{spoken} किलोमीटर प्रति घंटा"

        normalized = re.sub(r"(\d+)\s*(?:km\/h|kmph|किमी\/घंटा|किमी\s*प्रति\s*घंटा)\b", replace_speed, normalized)

        # 3. Percent / Humidity: e.g. 85%, 85 %
        def replace_percent(match: re.Match) -> str:
            val_str = match.group(1) or match.group(2)
            try:
                val = int(val_str)
                spoken = number_to_hindi(val)
            except (ValueError, TypeError):
                spoken = str(val_str)
            return f"{spoken} प्रतिशत"

        normalized = re.sub(r"(?:(\d+)\s*%|(\d+)\s*प्रतिशत)(?!\w)", replace_percent, normalized)

        # 4. Rainfall: e.g. 12 mm, 12 मिमी
        def replace_rain(match: re.Match) -> str:
            val_str = match.group(1)
            try:
                val = int(val_str)
                spoken = number_to_hindi(val)
            except ValueError:
                spoken = val_str
            return f"{spoken} मिलीमीटर"

        normalized = re.sub(r"(\d+)\s*(?:mm|मिमी|मिलीमीटर)\b", replace_rain, normalized)

        # 5. Pressure: e.g. 1012 hPa
        def replace_pressure(match: re.Match) -> str:
            val_str = match.group(1)
            try:
                val = int(val_str)
                spoken = number_to_hindi(val)
            except ValueError:
                spoken = val_str
            return f"{spoken} हेक्टोपास्कल"

        normalized = re.sub(r"(\d+)\s*(?:hPa|हेक्टोपास्कल)\b", replace_pressure, normalized)

        # 6. Times: e.g. 14:30, 08:00, 2:00 PM
        def replace_time(match: re.Match) -> str:
            h = int(match.group(1))
            m = int(match.group(2))
            period = "सुबह" if h < 12 else ("दोपहर" if h < 16 else ("शाम" if h < 20 else "रात"))
            h_12 = h if h <= 12 else (h - 12 if h > 12 else 12)
            if h == 0:
                h_12 = 12
            h_spoken = number_to_hindi(h_12)
            if m == 0:
                return f"{period} {h_spoken} बजे"
            elif m == 30:
                return f"{period} साढ़े {h_spoken} बजे"
            elif m == 15:
                return f"{period} सवा {h_spoken} बजे"
            elif m == 45:
                next_h = (h_12 % 12) + 1
                return f"{period} पौने {number_to_hindi(next_h)} बजे"
            else:
                return f"{period} {h_spoken} बजकर {number_to_hindi(m)} मिनट पर"

        normalized = re.sub(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", replace_time, normalized)

    else:
        # English normalization
        normalized = re.sub(r"(-?\d+)\s*(?:°C|°|deg\s*C)\b", r"\1 degrees Celsius", normalized)
        normalized = re.sub(r"(\d+)\s*(?:km\/h|kmph)\b", r"\1 kilometres per hour", normalized)
        normalized = re.sub(r"(\d+)\s*%", r"\1 percent", normalized)
        normalized = re.sub(r"(\d+)\s*mm\b", r"\1 millimetres", normalized)
        normalized = re.sub(r"(\d+)\s*hPa\b", r"\1 hectopascals", normalized)

    return normalized
