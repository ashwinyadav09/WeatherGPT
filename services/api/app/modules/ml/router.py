"""FastAPI Router for ML Registry, Models, Prediction, and Evaluation (Ticket R16).

Mounted under /v1/ml by discover_and_mount_routers in main.py.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from services.api.app.modules.ml.service import ml_service

router = APIRouter(prefix="/ml", tags=["ml"])


class PredictRequest(BaseModel):
    """Generic payload for /v1/ml/predict/{id}."""
    text: str | None = Field(default=None, description="Query text for intent classification or RAG")
    query: str | None = Field(default=None, description="Alternative query text parameter")
    language: str | None = Field(default=None, description="Language code (e.g. en, hi)")
    lat: float | None = Field(default=None, description="Latitude")
    lon: float | None = Field(default=None, description="Longitude")
    elev: float | None = Field(default=None, description="Elevation in meters")
    lead_day: int | None = Field(default=None, description="Forecast lead day (1 to 3)")
    raw_temp: float | None = Field(default=None, description="Raw NWP temperature for bias correction")
    forecast_tmax: float | None = Field(default=None, description="NWP forecast maximum temperature for risk prediction")
    metric: str | None = Field(default=None, description="Climate metric ('rain' or 'temperature')")
    top_k: int | None = Field(default=3, description="Number of results for RAG retrieval")


@router.get("/models")
async def list_models() -> list[dict[str, Any]]:
    """List all registered ML models with audited metrics from reports/metrics.json."""
    return ml_service.list_models()


@router.get("/models/{model_id}/card")
async def get_model_card(model_id: str) -> dict[str, Any]:
    """Retrieve model card and evaluation metrics for a specific model."""
    return ml_service.get_model_card(model_id)


@router.post("/predict/{model_id}")
async def predict_model(
    model_id: str,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Execute live inference on a registered model. Rejects if enabled_in_production=False."""
    return await ml_service.predict(model_id, payload)


@router.get("/eval/summary")
async def get_evaluation_summary() -> dict[str, Any]:
    """Aggregate evaluation summary across all models strictly from reports/metrics.json."""
    return ml_service.get_eval_summary()
