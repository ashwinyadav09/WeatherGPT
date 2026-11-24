"""Runtime service wrapper for intent classification and slot extraction (Ticket R12).

Provides:
- IntentService: loads trained TF-IDF + Calibrated Logistic Regression model.
- Threshold-based deterministic auto-routing (when confidence >= tau).
- Multilingual slot extraction (place, date_range, crop, hazard).
- Rule-based fallback if ML artifacts are unavailable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ml.intent.model import RuleIntentBaseline
from ml.intent.slot_parser import extract_slots

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "ml" / "intent" / "artifacts"
MODEL_FILE = ARTIFACTS_DIR / "intent_model.joblib"
METADATA_FILE = ARTIFACTS_DIR / "model_metadata.json"


@dataclass
class IntentPrediction:
    intent: str
    confidence: float
    slots: dict[str, Any] = field(default_factory=dict)
    auto_route: bool = False
    model_id: str = "intent_classifier_v1.0"
    model_version: str = "v1.0"


class IntentService:
    MODEL_ID = "intent_classifier_v1.0"
    MODEL_VERSION = "v1.0"

    def __init__(self, tau: float | None = None) -> None:
        self.pipeline: Any | None = None
        self.tau: float = tau if tau is not None else 0.68
        self.rule_fallback = RuleIntentBaseline()
        self._load_model()

    def _load_model(self) -> None:
        if not MODEL_FILE.exists():
            return

        try:
            import joblib

            self.pipeline = joblib.load(MODEL_FILE)
            if METADATA_FILE.exists():
                meta = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
                self.tau = float(meta.get("auto_route_threshold", self.tau))
        except Exception:
            self.pipeline = None

    def predict(self, text: str, language: str = "en") -> IntentPrediction:
        """Classify user query intent and extract multilingual slots."""
        slots = extract_slots(text)

        if self.pipeline is None:
            # Fallback to RuleIntentBaseline
            rule_res = self.rule_fallback.predict(text)
            # Merge slots
            merged_slots = dict(slots)
            for k, v in rule_res.slots.items():
                if v and not merged_slots.get(k):
                    merged_slots[k] = v

            canon_map = {
                "current": "current_conditions",
                "forecast": "forecast",
                "alert": "alert",
                "advisory": "advisory",
                "climate": "climate_history",
                "explain": "general_knowledge",
                "meta": "general_knowledge",
                "unsafe": "out_of_domain",
                "out_of_domain": "out_of_domain",
            }
            canon_intent = canon_map.get(rule_res.intent, "forecast")
            conf = float(rule_res.confidence)
            return IntentPrediction(
                intent=canon_intent,
                confidence=conf,
                slots=merged_slots,
                auto_route=conf >= self.tau,
                model_id=self.rule_fallback.MODEL_VERSION,
                model_version="v1.0",
            )

        # Use trained ML model
        try:
            import numpy as np

            probs = self.pipeline.predict_proba([text])[0]
            classes = self.pipeline.classes_
            best_idx = int(np.argmax(probs))
            best_intent = str(classes[best_idx])
            confidence = float(round(probs[best_idx], 4))

            # Out-of-vocabulary check: if query has fewer than 3 matching features
            # (e.g. scripts with low n-gram overlap where only a punctuation mark matched),
            # the statistical confidence is spurious and auto-route must be suppressed.
            tfidf = getattr(self.pipeline, "named_steps", {}).get("tfidf")
            feat_nnz = tfidf.transform([text]).nnz if tfidf is not None else 10
            if feat_nnz < 3:
                confidence = float(round(confidence * 0.1, 4))
                auto_route = False
            else:
                # Auto-route when calibrated confidence exceeds tau
                auto_route = confidence >= self.tau and best_intent not in ("general_knowledge",)

            return IntentPrediction(
                intent=best_intent,
                confidence=confidence,
                slots=slots,
                auto_route=auto_route,
                model_id=self.MODEL_ID,
                model_version=self.MODEL_VERSION,
            )
        except Exception:
            # Safe fallback if scikit-learn error
            rule_res = self.rule_fallback.predict(text)
            return IntentPrediction(
                intent=rule_res.intent,
                confidence=float(rule_res.confidence),
                slots=slots,
                auto_route=False,
                model_id=self.rule_fallback.MODEL_VERSION,
                model_version="v1.0",
            )

    def should_fallback_to_llm(self, pred: IntentPrediction) -> bool:
        """Determines whether planning should fall back to LLM."""
        return not pred.auto_route
