from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_PATH = ROOT / "ml" / "intent" / "datasets" / "golden.json"


@dataclass
class PredictionResult:
    intent: str
    confidence: float
    slots: dict[str, str] = field(default_factory=dict)
    model_version: str = "intent-multilingual-v1.0"


class IntentSlotModel:
    """Multilingual Intent and Slot classifier for weather inquiries.

    Classifies user queries into 8 intents: current, forecast, alert, advisory,
    climate, explain, meta, unsafe. Extracts places, time windows, and crops in milliseconds.
    """

    MODEL_VERSION = "intent-multilingual-v1.0"

    INTENT_KEYWORDS: dict[str, list[str]] = {
        "unsafe": [
            "ignore all previous",
            "system prompt",
            "reveal password",
            "secret keys",
            "सीक्रेट्स",
            "टोकन",
            "drop database",
            "disregard safety",
            "execute code",
        ],
        "meta": [
            "who created",
            "who built",
            "what languages",
            "कौन-कौन सी भाषा",
            "who are you",
            "tumhari sources",
            "what can you do",
            "help me understand",
        ],
        "explain": [
            "why does",
            "what causes",
            "explain how",
            "क्यों होती है",
            "क्यों होता है",
            "kaise aata hai",
            "explain karo",
            "causes heatwave",
            "western disturbances",
        ],
        "climate": [
            "compare to normal",
            "30-year normal",
            "long term climate",
            "climate trend",
            "सामान्य से कितनी",
            "monsoon anomaly",
            "baseline",
            "percentile",
        ],
        "advisory": [
            "advice",
            "advisory",
            "crop",
            "irrigate",
            "kheti",
            "सलाह",
            "फसल",
            "precautions for",
            "sugarcane",
            "wheat",
            "cotton",
            "mustard",
            "rice",
            "गन्ना",
            "गेहूं",
            "धान",
            "कपास",
            "सरसों",
        ],
        "alert": [
            "alert",
            "warning",
            "warnings",
            "cyclone",
            "तूफान",
            "चेतावनी",
            "अलर्ट",
            "thunderstorm warning",
            "severe weather",
        ],
        "forecast": [
            "tomorrow",
            "कल",
            "forecast",
            "weekend",
            "अगले",
            "अगला",
            "next week",
            "will it rain",
            "hogi kya",
            "expected max",
            "5 day",
            "7 day",
        ],
        "current": [
            "current",
            "right now",
            "abhi",
            "अभी",
            "temperature in",
            "raining in",
            "weather right now",
            "taapmaan",
            "conditions",
        ],
    }

    KNOWN_PLACES: list[tuple[str, str]] = [
        ("delhi", "Delhi"),
        ("नई दिल्ली", "Delhi"),
        ("दिल्ली", "Delhi"),
        ("mumbai", "Mumbai"),
        ("मुंबई", "Mumbai"),
        ("pune", "Pune"),
        ("पुणे", "Pune"),
        ("bengaluru", "Bengaluru"),
        ("बेंगलुरु", "Bengaluru"),
        ("bangalore", "Bengaluru"),
        ("chennai", "Chennai"),
        ("चेन्नई", "Chennai"),
        ("kolkata", "Kolkata"),
        ("कोलकाता", "Kolkata"),
        ("hyderabad", "Hyderabad"),
        ("हैदराबाद", "Hyderabad"),
        ("jaipur", "Jaipur"),
        ("जयपुर", "Jaipur"),
        ("shimla", "Shimla"),
        ("शिमला", "Shimla"),
        ("guwahati", "Guwahati"),
        ("गुवाहाटी", "Guwahati"),
        ("varanasi", "Varanasi"),
        ("वाराणसी", "Varanasi"),
        ("lucknow", "Lucknow"),
        ("लखनऊ", "Lucknow"),
        ("patna", "Patna"),
        ("पटना", "Patna"),
        ("bhopal", "Bhopal"),
        ("भोपाल", "Bhopal"),
        ("chandigarh", "Chandigarh"),
        ("चंडीगढ़", "Chandigarh"),
        ("ahmedabad", "Ahmedabad"),
        ("अहमदाबाद", "Ahmedabad"),
        ("srinagar", "Srinagar"),
        ("श्रीनगर", "Srinagar"),
        ("dehradun", "Dehradun"),
        ("देहरादून", "Dehradun"),
    ]

    KNOWN_CROPS: list[tuple[str, str]] = [
        ("sugarcane", "sugarcane"),
        ("गन्ने", "गन्ना"),
        ("गन्ना", "गन्ना"),
        ("wheat", "wheat"),
        ("गेहूं", "गेहूं"),
        ("rice", "rice"),
        ("धान", "धान"),
        ("cotton", "cotton"),
        ("कपास", "कपास"),
        ("mustard", "mustard"),
        ("सरसों", "सरसों"),
        ("gram", "gram"),
        ("चना", "चना"),
        ("soybean", "soybean"),
        ("सोयाबीन", "सोयाबीन"),
        ("maize", "maize"),
        ("मक्का", "मक्का"),
    ]

    TIME_PATTERNS: list[tuple[str, str]] = [
        (r"\b(right now|current|abhi|अभी)\b", "now"),
        (r"\b(tomorrow|कल|kal)\b", "tomorrow"),
        (r"\b(weekend)\b", "weekend"),
        (r"\b(7\s*days?|7\s*दिन)\b", "7 days"),
        (r"\b(5\s*days?|5\s*दिन)\b", "5 days"),
        (r"\b(next\s*week|agla\s*hafta)\b", "next week"),
    ]

    def load_golden_set(self) -> list[dict[str, Any]]:
        if not GOLDEN_PATH.exists():
            from ml.intent.dataset_generator import generate_dataset

            _, golden = generate_dataset()
            return golden
        with GOLDEN_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)

    def predict(self, text: str) -> PredictionResult:
        low = text.lower()

        # Score intents based on keyword matches
        scores: dict[str, float] = {k: 0.0 for k in self.INTENT_KEYWORDS}
        total_hits = 0

        for intent, kw_list in self.INTENT_KEYWORDS.items():
            for kw in kw_list:
                if kw in low:
                    weight = 2.5 if intent in ("unsafe", "meta", "explain") else 1.5
                    scores[intent] += weight
                    total_hits += 1

        # Check order of precedence: unsafe check always takes highest priority
        if scores["unsafe"] > 0:
            best_intent = "unsafe"
            confidence = 0.99
        elif total_hits == 0:
            # Low confidence fallback
            best_intent = "current"
            confidence = 0.35
        else:
            best_intent = max(scores, key=scores.get)
            max_score = scores[best_intent]
            confidence = min(0.98, round(0.70 + (max_score * 0.10), 2))

        # Extract slots
        slots: dict[str, str] = {}

        # Place slot
        for kw, canonical in self.KNOWN_PLACES:
            if kw.lower() in low or kw in text:
                slots["place"] = canonical
                break

        # Time slot
        for pat, canonical_time in self.TIME_PATTERNS:
            if re.search(pat, low, re.IGNORECASE):
                slots["time_window"] = canonical_time
                break

        # Crop slot
        for kw, canonical_crop in self.KNOWN_CROPS:
            if kw.lower() in low or kw in text:
                slots["crop"] = canonical_crop
                break

        return PredictionResult(
            intent=best_intent,
            confidence=confidence,
            slots=slots,
            model_version=self.MODEL_VERSION,
        )

    def should_fallback_to_llm(self, result: PredictionResult, threshold: float = 0.75) -> bool:
        """Determines if query routing should fall back to LLM due to low confidence."""
        return result.confidence < threshold or result.intent == "explain"
