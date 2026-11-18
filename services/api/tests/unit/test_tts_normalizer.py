from __future__ import annotations

from services.api.app.gateways.speech.tts_normalizer import normalize_for_tts, number_to_hindi


def test_number_to_hindi():
    assert number_to_hindi(0) == "शून्य"
    assert number_to_hindi(5) == "पांच"
    assert number_to_hindi(18) == "अठारह"
    assert number_to_hindi(32) == "बत्तीस"
    assert number_to_hindi(100) == "सौ"
    assert number_to_hindi(105) == "एक सौ पांच"
    assert number_to_hindi(1012) == "एक हज़ार बारह"


def test_normalize_for_tts_hindi_units():
    # Temperature
    t1 = normalize_for_tts("तापमान 32°C रहेगा", language="hi")
    assert "बत्तीस डिग्री सेल्सियस" in t1

    # Wind speed
    t2 = normalize_for_tts("हवा 15 km/h की गति से चलेगी", language="hi")
    assert "पंद्रह किलोमीटर प्रति घंटा" in t2

    # Humidity / Percentage
    t3 = normalize_for_tts("आर्द्रता 85% रहेगी", language="hi")
    assert "पचासी प्रतिशत" in t3

    # Rain
    t4 = normalize_for_tts("बारिश 12 mm संभावित है", language="hi")
    assert "बारह मिलीमीटर" in t4

    # Pressure
    t5 = normalize_for_tts("दबाव 1012 hPa है", language="hi")
    assert "एक हज़ार बारह हेक्टोपास्कल" in t5


def test_normalize_for_tts_hindi_times():
    # Standard time
    t1 = normalize_for_tts("अपडेट समय 14:00", language="hi")
    assert "दोपहर दो बजे" in t1

    # Half past
    t2 = normalize_for_tts("पूर्वानुमान 08:30 बजे", language="hi")
    assert "सुबह साढ़े आठ बजे" in t2

    # Quarter past
    t3 = normalize_for_tts("बारिश 16:15 पर", language="hi")
    assert "शाम सवा चार बजे" in t3


def test_normalize_for_tts_english():
    res = normalize_for_tts("Temp 32°C, wind 15 km/h, humidity 85%, rain 12 mm", language="en")
    assert "32 degrees Celsius" in res
    assert "15 kilometres per hour" in res
    assert "85 percent" in res
    assert "12 millimetres" in res
