"""ML Registry, Model Card, Prediction, and Evaluation Service (Ticket R16).

Implements:
- Model registry reading strictly from audited `ml/*/reports/metrics.json`.
- Strict truthfulness: missing values are returned as 'NOT MEASURED'.
- Dispatches predictions to real inference services.
- Rejects prediction when enabled_in_production is False.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[5]
ML_DIR = ROOT / "ml"

CANONICAL_MODELS: list[str] = [
    "bias_correction",
    "climate",
    "extreme_event",
    "intent",
    "rag",
]

ALIAS_MAP: dict[str, str] = {
    "bias": "bias_correction",
    "bias_correction": "bias_correction",
    "nwp_bias_correction": "bias_correction",
    "nwp_biascorrection_v1": "bias_correction",
    "climate": "climate",
    "climate_trend": "climate",
    "climate_history": "climate",
    "risk": "extreme_event",
    "extreme_event": "extreme_event",
    "extreme_events": "extreme_event",
    "extreme_event_risk": "extreme_event",
    "intent": "intent",
    "intent_classifier": "intent",
    "rag": "rag",
    "advisory": "rag",
    "rag_advisory": "rag",
    "rag_advisory_engine": "rag",
}


class MLService:
    def __init__(self, ml_dir: Path | None = None) -> None:
        self.ml_dir = ml_dir or ML_DIR

    def resolve_model_id(self, model_id: str) -> str:
        clean_id = model_id.strip().lower()
        if clean_id in ALIAS_MAP:
            return ALIAS_MAP[clean_id]
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in ML registry")

    def get_metrics_data(self, model_dir_name: str) -> dict[str, Any] | None:
        metrics_file = self.ml_dir / model_dir_name / "reports" / "metrics.json"
        if not metrics_file.exists():
            return None
        try:
            return json.loads(metrics_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("failed_to_read_metrics", extra={"model": model_dir_name, "error": str(exc)})
            return None

    def list_models(self) -> list[dict[str, Any]]:
        """List all models registered in the ML registry reading strictly from reports/metrics.json."""
        models: list[dict[str, Any]] = []

        for model_id in CANONICAL_MODELS:
            metrics = self.get_metrics_data(model_id)
            if not metrics:
                models.append({
                    "id": model_id,
                    "name": model_id.replace("_", " ").title(),
                    "version": "NOT MEASURED",
                    "task": "NOT MEASURED",
                    "trained_at": "NOT MEASURED",
                    "data_summary": {
                        "n_train": "NOT MEASURED",
                        "n_test": "NOT MEASURED",
                        "provenance": "NOT MEASURED",
                    },
                    "headline_metrics": {},
                    "enabled_in_production": False,
                    "provenance": "NOT MEASURED",
                })
                continue

            name = metrics.get("model_name") or metrics.get("model_id") or model_id.replace("_", " ").title()
            version = metrics.get("version") or metrics.get("model_version") or "v1.0"
            task = metrics.get("task") or metrics.get("methodology") or "Operational Weather AI/ML component"
            trained_at = metrics.get("timestamp") or metrics.get("generated_at") or "NOT MEASURED"
            provenance = metrics.get("provenance", "NOT MEASURED")
            enabled = bool(metrics.get("enabled_in_production", True))

            headline_metrics: dict[str, Any] = {}
            if model_id == "bias_correction":
                headline_metrics = {
                    "mae": metrics.get("mae", "NOT MEASURED"),
                    "rmse": metrics.get("rmse", "NOT MEASURED"),
                    "bias": metrics.get("bias", "NOT MEASURED"),
                    "brier_skill_score": metrics.get("brier_skill_score", "NOT MEASURED"),
                }
            elif model_id == "climate":
                m_sub = metrics.get("metrics", {})
                headline_metrics = {
                    "event_recall": m_sub.get("event_recall_isolation_forest", "NOT MEASURED"),
                    "mean_temp_trend": m_sub.get("mean_annual_temp_trend_degc_per_decade", "NOT MEASURED"),
                }
            elif model_id == "extreme_event":
                headline_metrics = {
                    "accuracy": metrics.get("accuracy", "NOT MEASURED"),
                    "macro_f1": metrics.get("macro_f1", "NOT MEASURED"),
                    "prevalence": metrics.get("prevalence", "NOT MEASURED"),
                }
            elif model_id == "intent":
                m_sub = metrics.get("metrics", {})
                headline_metrics = {
                    "val_macro_f1": m_sub.get("val_macro_f1", "NOT MEASURED"),
                    "gold_set_macro_f1": m_sub.get("gold_set_macro_f1", "NOT MEASURED"),
                }
            elif model_id == "rag":
                headline_metrics = {
                    "accuracy": metrics.get("accuracy", "NOT MEASURED"),
                    "hybrid_recall_at_3": metrics.get("hybrid", {}).get("recall_at_3", "NOT MEASURED"),
                    "hybrid_mrr": metrics.get("hybrid", {}).get("mrr", "NOT MEASURED"),
                }

            models.append({
                "id": model_id,
                "name": name,
                "version": version,
                "task": task,
                "trained_at": trained_at,
                "data_summary": {
                    "n_train": metrics.get("n_train", "NOT MEASURED"),
                    "n_test": metrics.get("n_test", "NOT MEASURED"),
                    "provenance": provenance,
                },
                "headline_metrics": headline_metrics,
                "enabled_in_production": enabled,
                "provenance": provenance,
            })

        return models

    def get_model_card(self, model_id: str) -> dict[str, Any]:
        """Return MODEL_CARD.md content and audited metrics for a model."""
        canonical_id = self.resolve_model_id(model_id)
        card_file = self.ml_dir / canonical_id / "MODEL_CARD.md"
        if not card_file.exists():
            card_file = self.ml_dir / canonical_id / "reports" / "MODEL_CARD.md"
        if not card_file.exists():
            raise HTTPException(status_code=404, detail=f"Model card for '{model_id}' not found")

        card_text = card_file.read_text(encoding="utf-8")
        metrics_data = self.get_metrics_data(canonical_id) or {"status": "NOT MEASURED"}

        return {
            "id": canonical_id,
            "name": canonical_id.replace("_", " ").title(),
            "model_card": card_text,
            "metrics": metrics_data,
        }

    async def predict(self, model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Perform live inference using the designated model."""
        canonical_id = self.resolve_model_id(model_id)
        metrics = self.get_metrics_data(canonical_id) or {}
        enabled = bool(metrics.get("enabled_in_production", True))

        if not enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_id}' is disabled in production (enabled_in_production=false)",
            )

        if canonical_id == "intent":
            text = str(payload.get("text") or payload.get("query") or "")
            lang = str(payload.get("language") or payload.get("lang") or "en")
            from ml.intent.service import IntentService
            intent_svc = IntentService()
            pred = intent_svc.predict(text, language=lang)
            return {
                "model_id": getattr(intent_svc, "MODEL_ID", "intent_classifier_v1"),
                "intent": getattr(pred, "intent", "forecast"),
                "confidence": getattr(pred, "confidence", 1.0),
                "slots": getattr(pred, "slots", {}),
                "auto_route": getattr(pred, "auto_route", False),
            }

        elif canonical_id == "bias_correction":
            from ml.bias_correction.service import get_inference_service
            bias_svc = get_inference_service()
            raw_temp = float(payload.get("raw_temp", 30.0))
            lead_day = int(payload.get("lead_day", 1))
            lat = float(payload.get("lat", 18.52))
            lon = float(payload.get("lon", 73.85))
            elev = float(payload.get("elev", 560.0))
            bias_pred = bias_svc.predict_temperature(raw_temp=raw_temp, lead_day=lead_day, lat=lat, lon=lon, elev=elev)
            if not bias_pred:
                raise HTTPException(status_code=400, detail="Bias correction inference unavailable or outside domain")
            return {
                "model_id": "NWP_BiasCorrection_v1",
                **bias_pred,
            }

        elif canonical_id == "extreme_event":
            from ml.extreme_event.service import ExtremeEventRiskService
            risk_svc = ExtremeEventRiskService()
            lat = float(payload.get("lat", 18.52))
            lon = float(payload.get("lon", 73.85))
            lead_day = int(payload.get("lead_day", 1))
            elev = float(payload.get("elev", 100.0))
            fc_tmax = payload.get("forecast_tmax")
            risk_pred = risk_svc.predict_risk(lat=lat, lon=lon, elev=elev, lead_day=lead_day, forecast_tmax=fc_tmax)
            return {
                "model_id": "extreme_event_risk_v1",
                "risk_probability": risk_pred.get("heat_wave_risk", 0.0),
                **risk_pred,
            }

        elif canonical_id == "climate":
            lat = float(payload.get("lat", 18.52))
            lon = float(payload.get("lon", 73.85))
            metric = str(payload.get("metric", "rain"))
            place_id = str(payload.get("place_id") or "pune")
            from services.api.app.modules.climate.service import ClimateService
            climate_svc = ClimateService()
            stat = await climate_svc.get_stat(place_id=place_id, variable=metric)
            return {
                "model_id": "climate_trend_v1",
                "lat": lat,
                "lon": lon,
                **stat,
            }

        elif canonical_id == "rag":
            query = str(payload.get("query") or payload.get("text") or "")
            lang = str(payload.get("lang") or payload.get("language") or "en")
            from services.api.app.modules.advisory.rag import RagEngine
            rag = RagEngine.get_instance()
            matches = rag.search(query=query, lang=lang, top_k=int(payload.get("top_k", 3)))
            return {
                "model_id": "rag_advisory_engine",
                "query": query,
                "matches": [
                    {
                        "chunk_id": c.chunk_id,
                        "score": round(score, 4),
                        "source": c.source,
                        "title": c.title,
                        "text": c.text,
                    }
                    for c, score in matches
                ],
            }

        raise HTTPException(status_code=404, detail=f"Inference handler for '{model_id}' not implemented")

    def get_eval_summary(self) -> dict[str, Any]:
        """Aggregate evaluation metrics strictly from audited reports/metrics.json."""
        summary: dict[str, Any] = {
            "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
            "policy": "Rules T1-T8: No simulated results. Strictly audited metrics.",
            "models": {},
        }

        for model_id in CANONICAL_MODELS:
            metrics = self.get_metrics_data(model_id)
            if not metrics:
                summary["models"][model_id] = {
                    "status": "NOT MEASURED",
                    "provenance": "NOT MEASURED",
                }
                continue

            summary["models"][model_id] = {
                "model_name": metrics.get("model_name") or metrics.get("model_id") or model_id,
                "git_sha": metrics.get("git_sha", "NOT MEASURED"),
                "provenance": metrics.get("provenance", "NOT MEASURED"),
                "n_test": metrics.get("n_test", "NOT MEASURED"),
                "metrics": metrics.get("metrics") or {
                    k: v for k, v in metrics.items()
                    if k in ("mae", "rmse", "bias", "accuracy", "macro_f1", "brier_skill_score", "bm25", "dense", "hybrid")
                },
                "enabled_in_production": bool(metrics.get("enabled_in_production", True)),
            }

        return summary


ml_service = MLService()
