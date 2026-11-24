"""Seam and Contract Tests for ML API (Ticket R16).

Tests:
- GET /v1/ml/models
- GET /v1/ml/models/{id}/card
- POST /v1/ml/predict/{id}
- GET /v1/ml/eval/summary
- Rejection of prediction when enabled_in_production=False
- Missing metrics return 'NOT MEASURED'
"""
from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api.app.main import app

client = TestClient(app)


def test_list_models_returns_all_canonical_models():
    """Verify /v1/ml/models returns all canonical models with required fields."""
    response = client.get("/v1/ml/models")
    assert response.status_code == 200
    models = response.json()
    assert isinstance(models, list)
    assert len(models) >= 5

    model_ids = {m["id"] for m in models}
    expected_ids = {"bias_correction", "climate", "extreme_event", "intent", "rag"}
    assert expected_ids.issubset(model_ids)

    for m in models:
        assert "id" in m
        assert "name" in m
        assert "version" in m
        assert "task" in m
        assert "trained_at" in m
        assert "data_summary" in m
        assert "headline_metrics" in m
        assert "enabled_in_production" in m
        assert "provenance" in m
        assert m["provenance"] in ("recorded_real_http", "human_labels", "NOT MEASURED")


def test_list_models_missing_metrics_returns_not_measured():
    """Verify that a missing metrics.json returns 'NOT MEASURED' without failing."""
    with patch("services.api.app.modules.ml.service.ml_service.get_metrics_data", return_value=None):
        response = client.get("/v1/ml/models")
        assert response.status_code == 200
        models = response.json()
        for m in models:
            assert m["version"] == "NOT MEASURED"
            assert m["task"] == "NOT MEASURED"
            assert m["data_summary"]["provenance"] == "NOT MEASURED"


def test_get_model_card_and_aliases():
    """Verify /v1/ml/models/{id}/card returns card and handles aliases."""
    # Canonical ID
    res1 = client.get("/v1/ml/models/bias_correction/card")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["id"] == "bias_correction"
    assert "model_card" in data1
    assert len(data1["model_card"]) > 50

    # Aliases
    for alias, canon in [("bias", "bias_correction"), ("rag", "rag"), ("risk", "extreme_event"), ("climate", "climate")]:
        res_alias = client.get(f"/v1/ml/models/{alias}/card")
        assert res_alias.status_code == 200
        assert res_alias.json()["id"] == canon

    # 404 on unknown model
    res_404 = client.get("/v1/ml/models/non_existent_model_xyz/card")
    assert res_404.status_code == 404


def test_predict_model_endpoints():
    """Verify POST /v1/ml/predict/{id} dispatches to real inference services."""
    # 1. Intent prediction
    res_intent = client.post("/v1/ml/predict/intent", json={"text": "Will it rain tomorrow in Pune?", "language": "en"})
    assert res_intent.status_code == 200
    intent_data = res_intent.json()
    assert "intent" in intent_data
    assert "confidence" in intent_data

    # 2. Risk prediction
    res_risk = client.post("/v1/ml/predict/risk", json={"lat": 18.52, "lon": 73.85, "lead_day": 1, "elev": 560.0, "forecast_tmax": 38.0})
    assert res_risk.status_code == 200
    risk_data = res_risk.json()
    assert "risk_probability" in risk_data
    assert "risk_level" in risk_data

    # 3. Climate prediction
    res_clim = client.post("/v1/ml/predict/climate", json={"lat": 18.52, "lon": 73.85, "metric": "rain"})
    assert res_clim.status_code == 200
    clim_data = res_clim.json()
    assert "sen_slope" in clim_data or "trend_sen_slope" in clim_data or "variable" in clim_data

    # 4. RAG prediction
    res_rag = client.post("/v1/ml/predict/rag", json={"query": "heat wave drinking water precautions", "lang": "en"})
    assert res_rag.status_code == 200
    rag_data = res_rag.json()
    assert "matches" in rag_data
    assert len(rag_data["matches"]) >= 1


def test_predict_disabled_model_rejection():
    """Verify that a model with enabled_in_production=False is rejected with HTTP 400."""
    fake_metrics = {"enabled_in_production": False}
    with patch("services.api.app.modules.ml.service.ml_service.get_metrics_data", return_value=fake_metrics):
        response = client.post("/v1/ml/predict/intent", json={"text": "test query"})
        assert response.status_code == 400
        data = response.json()
        err_msg = data.get("detail") or data.get("error", {}).get("message", "")
        assert "disabled in production" in err_msg


def test_get_eval_summary():
    """Verify GET /v1/ml/eval/summary aggregates audited metrics."""
    response = client.get("/v1/ml/eval/summary")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert "models" in data
    assert "bias_correction" in data["models"]
    assert "rag" in data["models"]
    assert "climate" in data["models"]
    assert "extreme_event" in data["models"]
    assert "intent" in data["models"]
