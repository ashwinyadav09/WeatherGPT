"""Dataset builder and preprocessor for Intent & Slot classification (Ticket R12).

Maps MASSIVE multilingual utterances and project domain seeds to the 7 canonical labels:
- current_conditions
- forecast
- alert
- advisory
- climate_history
- general_knowledge
- out_of_domain

Rule T3 & R12 compliance:
- Every row contains a `source` column ('massive' or 'human_seed').
- Zero synthetic data in test sets.
- Generates train and validation sets with stratified splits.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "ml" / "intent" / "data"
RAW_MASSIVE_DIR = DATA_DIR / "raw" / "massive"
PROCESSED_FILE = DATA_DIR / "processed_dataset.csv"

CANONICAL_INTENTS = [
    "current_conditions",
    "forecast",
    "alert",
    "advisory",
    "climate_history",
    "general_knowledge",
    "out_of_domain",
]

# Language mappings: MASSIVE locale -> project 2-letter language code
LOCALE_MAP = {
    "en-US": "en",
    "hi-IN": "hi",
    "bn-BD": "bn",
    "ta-IN": "ta",
    "te-IN": "te",
}

# Project domain seeds across languages
SEED_QUERIES: list[dict[str, Any]] = [
    # Advisory seeds
    {"text": "When should I irrigate wheat in Punjab?", "lang": "en", "intent": "advisory", "source": "human_seed"},
    {"text": "What is the agromet advisory for sugarcane in Pune?", "lang": "en", "intent": "advisory", "source": "human_seed"},
    {"text": "Precautions for cotton crop during pest attack", "lang": "en", "intent": "advisory", "source": "human_seed"},
    {"text": "Is it safe to spray pesticides during high winds?", "lang": "en", "intent": "advisory", "source": "human_seed"},
    {"text": "Heat wave safety precautions for outdoor farm workers", "lang": "en", "intent": "advisory", "source": "human_seed"},
    {"text": "Cold wave protection measures for mustard crop", "lang": "en", "intent": "advisory", "source": "human_seed"},
    {"text": "Fisherfolk advisory: sea condition warning for coastal Gujarat", "lang": "en", "intent": "advisory", "source": "human_seed"},
    {"text": "Should I apply fertilizer before expected rainfall?", "lang": "en", "intent": "advisory", "source": "human_seed"},
    {"text": "गेहूं में पहली सिंचाई कब करें?", "lang": "hi", "intent": "advisory", "source": "human_seed"},
    {"text": "पुणे में गन्ने की फसल के लिए क्या सलाह है?", "lang": "hi", "intent": "advisory", "source": "human_seed"},
    {"text": "कपास में कीट नियंत्रण के उपाय क्या हैं?", "lang": "hi", "intent": "advisory", "source": "human_seed"},
    {"text": "लू से बचने के लिए किसानों को क्या करना चाहिए?", "lang": "hi", "intent": "advisory", "source": "human_seed"},
    {"text": "शीतलहर से सरसों की फसल को कैसे बचाएं?", "lang": "hi", "intent": "advisory", "source": "human_seed"},
    {"text": "धान की फसल में जल प्रबंधन की सलाह दें", "lang": "hi", "intent": "advisory", "source": "human_seed"},
    {"text": "মাঠে ধান কাটার উপযুক্ত সময় কখন?", "lang": "bn", "intent": "advisory", "source": "human_seed"},
    {"text": "ভুট্টা চাষে সেচের সঠিক সময় কখন?", "lang": "bn", "intent": "advisory", "source": "human_seed"},
    {"text": "गव्हाला पहिले पाणी कधी द्यावे?", "lang": "mr", "intent": "advisory", "source": "human_seed"},
    {"text": "उसाच्या पिकासाठी सल्ला काय आहे?", "lang": "mr", "intent": "advisory", "source": "human_seed"},
    {"text": "గోధుమ పంటకు మొదటి నీటి తడి ఎప్పుడు ఇవ్వాలి?", "lang": "te", "intent": "advisory", "source": "human_seed"},
    {"text": "వరి పంటలో నీటి యాజమాన్యం ఎలా ఉండాలి?", "lang": "te", "intent": "advisory", "source": "human_seed"},
    {"text": "கோதுமை பயிருக்கு எப்போது நீர் பாய்ச்ச வேண்டும்?", "lang": "ta", "intent": "advisory", "source": "human_seed"},
    {"text": "கரும்பு பயிருக்கான வேளாண் ஆலோசனை என்ன?", "lang": "ta", "intent": "advisory", "source": "human_seed"},

    # Alert seeds
    {"text": "Is there any cyclone warning for Odisha coast?", "lang": "en", "intent": "alert", "source": "human_seed"},
    {"text": "Show thunderstorm alerts for West Bengal", "lang": "en", "intent": "alert", "source": "human_seed"},
    {"text": "Any flood warning issued for Assam districts?", "lang": "en", "intent": "alert", "source": "human_seed"},
    {"text": "Heavy rainfall red alert status for Mumbai", "lang": "en", "intent": "alert", "source": "human_seed"},
    {"text": "Lightning warning and safety guidance for Bihar", "lang": "en", "intent": "alert", "source": "human_seed"},
    {"text": "NDMA heatwave alert level for Rajasthan today", "lang": "en", "intent": "alert", "source": "human_seed"},
    {"text": "क्या ओडिशा में चक्रवात की चेतावनी है?", "lang": "hi", "intent": "alert", "source": "human_seed"},
    {"text": "दिल्ली में भारी बारिश का अलर्ट जारी हुआ है क्या?", "lang": "hi", "intent": "alert", "source": "human_seed"},
    {"text": "मुंबई के लिए रेड अलर्ट की स्थिति क्या है?", "lang": "hi", "intent": "alert", "source": "human_seed"},
    {"text": "राजस्थान में लू की चेतावनी है क्या?", "lang": "hi", "intent": "alert", "source": "human_seed"},
    {"text": "पश्चिम बंगाल में आंधी तूफान का अलर्ट", "lang": "hi", "intent": "alert", "source": "human_seed"},
    {"text": "ঘূর্ণিঝড় সতর্কতা জারি আছে কি?", "lang": "bn", "intent": "alert", "source": "human_seed"},
    {"text": "ভারী বৃষ্টির লাল সতর্কতা", "lang": "bn", "intent": "alert", "source": "human_seed"},
    {"text": "चक्रीवादळाचा इशारा दिला आहे का?", "lang": "mr", "intent": "alert", "source": "human_seed"},
    {"text": "मुसळधार पावसाचा रेड अलर्ट आहे का?", "lang": "mr", "intent": "alert", "source": "human_seed"},
    {"text": "తుఫాను హెచ్చరిక జారీ చేయబడిందా?", "lang": "te", "intent": "alert", "source": "human_seed"},
    {"text": "భారీ వర్షాల రెడ్ అలర్ట్ సమాచారం", "lang": "te", "intent": "alert", "source": "human_seed"},
    {"text": "புயல் எச்சரிக்கை விடுக்கப்பட்டுள்ளதா?", "lang": "ta", "intent": "alert", "source": "human_seed"},
    {"text": "சென்னையில் கனமழை எச்சரிக்கை நிலை என்ன?", "lang": "ta", "intent": "alert", "source": "human_seed"},

    # Climate history seeds
    {"text": "How does this May temperature in Jaipur compare to normal?", "lang": "en", "intent": "climate_history", "source": "human_seed"},
    {"text": "What is the 30-year normal rainfall for Nagpur in July?", "lang": "en", "intent": "climate_history", "source": "human_seed"},
    {"text": "Has monsoon rainfall changed in my district since 1990?", "lang": "en", "intent": "climate_history", "source": "human_seed"},
    {"text": "Temperature anomaly and historical percentile for Delhi", "lang": "en", "intent": "climate_history", "source": "human_seed"},
    {"text": "Long term climate trend for summer maximum temperatures", "lang": "en", "intent": "climate_history", "source": "human_seed"},
    {"text": "जयपुर में मई का तापमान सामान्य से कितना अलग है?", "lang": "hi", "intent": "climate_history", "source": "human_seed"},
    {"text": "नागपुर में 30 साल की सामान्य बारिश क्या है?", "lang": "hi", "intent": "climate_history", "source": "human_seed"},
    {"text": "1990 से अब तक मानसून की बारिश में क्या बदलाव आया है?", "lang": "hi", "intent": "climate_history", "source": "human_seed"},
    {"text": "दिल्ली में तापमान सामान्य से कितना ज्यादा या कम है?", "lang": "hi", "intent": "climate_history", "source": "human_seed"},
    {"text": "জলবায়ুর দীর্ঘমেয়াদী পরিবর্তন কেমন হয়েছে?", "lang": "bn", "intent": "climate_history", "source": "human_seed"},
    {"text": "पुण्यात सरासरीपेक्षा जास्त पाऊस झाला का?", "lang": "mr", "intent": "climate_history", "source": "human_seed"},
    {"text": "సాధారణ వర్షపాతం కంటే ఇది ఎక్కువా లేక తక్కువా?", "lang": "te", "intent": "climate_history", "source": "human_seed"},
    {"text": "இயல்பான மழையை விட இது அதிகமா?", "lang": "ta", "intent": "climate_history", "source": "human_seed"},

    # Out of domain (Aviation questions explicitly recognised)
    {"text": "Can I get the METAR and TAF briefing for Delhi airport?", "lang": "en", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "What are the runway visibility conditions for pilot briefing?", "lang": "en", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "Flight route weather briefing for flight AI 101", "lang": "en", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "Aviation weather forecast for IFR approach into Mumbai", "lang": "en", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "दिल्ली एयरपोर्ट के लिए पायलट मौसम ब्रीफिंग", "lang": "hi", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "उड़ान भरने के लिए रनवे की दृश्यता क्या है?", "lang": "hi", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "বিমানবন্দরের আবহাওয়া কেমন?", "lang": "bn", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "विमान उड्डाणासाठी धावपट्टीवरील हवामान कसे आहे?", "lang": "mr", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "విమాన ప్రయాణానికి వాతావరణం అనుకూలంగా ఉందా?", "lang": "te", "intent": "out_of_domain", "source": "human_seed"},
    {"text": "விமான நிலைய வானிலை முன்னறிவிப்பு என்ன?", "lang": "ta", "intent": "out_of_domain", "source": "human_seed"},

    # General knowledge / Meta
    {"text": "What causes western disturbances in northern India?", "lang": "en", "intent": "general_knowledge", "source": "human_seed"},
    {"text": "Explain why sea breeze cools coastal cities in the evening", "lang": "en", "intent": "general_knowledge", "source": "human_seed"},
    {"text": "Who built WeatherGPT and what models power it?", "lang": "en", "intent": "general_knowledge", "source": "human_seed"},
    {"text": "What does an orange alert mean in IMD weather warnings?", "lang": "en", "intent": "general_knowledge", "source": "human_seed"},
    {"text": "पश्चिमी विक्षोभ क्या होता है?", "lang": "hi", "intent": "general_knowledge", "source": "human_seed"},
    {"text": "ऑरेंज अलर्ट का क्या मतलब होता है?", "lang": "hi", "intent": "general_knowledge", "source": "human_seed"},
    {"text": "यह मौसम की जानकारी कहां से आती है?", "lang": "hi", "intent": "general_knowledge", "source": "human_seed"},
]


def _categorize_massive_record(scenario: str, utt: str, intent_label: str) -> str:
    """Map MASSIVE record to one of our 7 canonical intent labels."""
    low = utt.lower()

    if scenario == "weather":
        # Check current conditions keywords
        if any(w in low for w in ["now", "right now", "outside", "current", "currently", "degrees right now", "अभी", "বর্তমানে", "ఇప్పుడు", "இப்போது"]):
            return "current_conditions"
        # Check climate keywords
        if any(w in low for w in ["normal", "average", "typical", "history", "सामान्य", "గత", "வழக்கமான"]):
            return "climate_history"
        # Most weather queries are forecasts
        return "forecast"

    elif scenario == "general":
        return "general_knowledge"

    elif scenario == "transport":
        # Flight/aviation questions -> out_of_domain
        if any(w in low for w in ["flight", "plane", "airport", "flying", "fly", "pilot", "उड़ान", "विमान", "விமானம்", "విమానం"]):
            return "out_of_domain"
        return "out_of_domain"

    else:
        # Other non-weather domains (music, alarm, audio, calendar, iot, cooking, email)
        return "out_of_domain"


def build_processed_dataset(max_samples_per_intent: int = 1500) -> list[dict[str, Any]]:
    """Build training dataset from MASSIVE JSONL files and domain seeds."""
    all_rows: list[dict[str, Any]] = []

    # 1. Add Domain Seeds
    for seed in SEED_QUERIES:
        all_rows.append({
            "text": seed["text"],
            "lang": seed["lang"],
            "intent": seed["intent"],
            "source": seed["source"],
        })

    # 2. Ingest MASSIVE JSONL files
    counts_by_intent: dict[str, int] = {k: 0 for k in CANONICAL_INTENTS}
    for r in all_rows:
        counts_by_intent[r["intent"]] += 1

    for locale, lang_code in LOCALE_MAP.items():
        jsonl_path = RAW_MASSIVE_DIR / f"{locale}.jsonl"
        if not jsonl_path.exists():
            continue

        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    scenario = rec.get("scenario", "")
                    utt = rec.get("utt", "").strip()
                    intent_raw = rec.get("intent", "")

                    if not utt:
                        continue

                    canonical_intent = _categorize_massive_record(scenario, utt, intent_raw)

                    # Cap per intent to prevent massive class imbalance
                    if counts_by_intent[canonical_intent] < max_samples_per_intent:
                        all_rows.append({
                            "text": utt,
                            "lang": lang_code,
                            "intent": canonical_intent,
                            "source": "massive",
                        })
                        counts_by_intent[canonical_intent] += 1
                except Exception:
                    continue

    print(f"Total dataset built: {len(all_rows)} rows across {len(LOCALE_MAP)} languages.")
    print("Class distribution:", counts_by_intent)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with PROCESSED_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "lang", "intent", "source"])
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"[OK] Saved processed dataset to {PROCESSED_FILE}")

    return all_rows


def load_dataset() -> list[dict[str, Any]]:
    if not PROCESSED_FILE.exists():
        return build_processed_dataset()
    rows = []
    with PROCESSED_FILE.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(dict(r))
    return rows


def get_stratified_splits(
    rows: list[dict[str, Any]], val_ratio: float = 0.20, seed: int = 42
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministically partition dataset into train and validation sets per class."""
    by_intent: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_intent.setdefault(r["intent"], []).append(r)

    train_rows: list[dict[str, Any]] = []
    val_rows: list[dict[str, Any]] = []

    for intent, items in by_intent.items():
        n = len(items)
        n_val = max(1, int(n * val_ratio))
        # Deterministic split based on fixed hash order
        sorted_items = sorted(items, key=lambda x: f"{x['lang']}_{x['text']}")
        val_rows.extend(sorted_items[:n_val])
        train_rows.extend(sorted_items[n_val:])

    return train_rows, val_rows


if __name__ == "__main__":
    build_processed_dataset()
