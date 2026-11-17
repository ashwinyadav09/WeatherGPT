from __future__ import annotations

from services.api.app.conversation.i18n import (
    check_hindi_glossary,
    detect_language,
    get_hindi_probability_phrase,
    get_hindi_rainfall_phrase,
    normalize_for_speech_hi,
)


def test_detect_language():
    assert detect_language("कल पुणे में बारिश होगी क्या?") == "hi"
    assert detect_language("Will it rain tomorrow in Pune?") == "en"
    assert detect_language("Kya kal Mumbai me barish hogi?") == "hi"
    assert detect_language("Delhi me kal rain expect kar sakte hain?") == "hi"
    assert detect_language("What is the temperature in Bengaluru?") == "en"


def test_hindi_probability_phrases():
    assert get_hindi_probability_phrase(5) == "बहुत कम संभावना"
    assert get_hindi_probability_phrase(20) == "कम संभावना"
    assert get_hindi_probability_phrase(45) == "संभावना है"
    assert get_hindi_probability_phrase(70) == "काफ़ी संभावना"
    assert get_hindi_probability_phrase(90) == "बहुत अधिक संभावना"


def test_hindi_rainfall_phrases():
    assert "शुष्क" in get_hindi_rainfall_phrase(0.0) or "बारिश नहीं" in get_hindi_rainfall_phrase(0.0)
    assert get_hindi_rainfall_phrase(1.5) == "बहुत हल्की बारिश"
    assert get_hindi_rainfall_phrase(10.0) == "हल्की बारिश"
    assert get_hindi_rainfall_phrase(35.0) == "मध्यम बारिश"
    assert get_hindi_rainfall_phrase(80.0) == "भारी बारिश"
    assert get_hindi_rainfall_phrase(150.0) == "बहुत भारी बारिश"
    assert get_hindi_rainfall_phrase(250.0) == "अत्यंत भारी बारिश"


def test_check_hindi_glossary():
    valid_text = "कल पुणे में हल्की बारिश की संभावना है और तापमान २८ डिग्री सेल्सियस रहेगा।"
    res_valid = check_hindi_glossary(valid_text)
    assert res_valid.is_valid is True

    forbidden_text = "बारिश होने की पूरी गारंटी है।"
    res_forbidden = check_hindi_glossary(forbidden_text)
    assert res_forbidden.is_valid is False
    assert any("गारंटी" in err for err in res_forbidden.errors)


def test_normalize_for_speech_hi():
    normalized = normalize_for_speech_hi("तापमान 28.5 degC और बारिश 12 mm रहेगी")
    assert "डिग्री सेल्सियस" in normalized
    assert "मिलीमीटर" in normalized
