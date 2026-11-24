"""Unit tests for extreme-event risk classification and feasibility gates (Ticket R14)."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import pytest

from ml.extreme_event.dataset import PROCESSED_FILE, load_extreme_event_data
from ml.extreme_event.eda import evaluate_hazards
from ml.extreme_event.service import ExtremeEventRiskService
from services.api.app.agent.tools import get_risk_outlook
from services.api.app.evidence.models import EvidencePacket

ROOT = Path(__file__).resolve().parents[4]


def test_feasibility_gate_and_counts() -> None:
    """Verify that hazard event counts satisfy the feasibility gate rules."""
    metrics_path = ROOT / "ml" / "extreme_event" / "reports" / "metrics.json"
    with open(metrics_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    gate = metrics["feasibility_gate"]
    assert gate["heatwave"]["status"] == "kept"
    assert gate["heatwave"]["train_events"] >= 50
    assert gate["heatwave"]["test_events"] >= 20
    assert gate["cold_wave"]["status"] == "excluded"
    assert gate["heavy_rain"]["status"] == "excluded"

    # If raw data files are available locally, also dynamically verify evaluate_hazards()
    raw_dir = ROOT / "ml" / "bias_correction" / "data" / "raw"
    if raw_dir.exists() and list(raw_dir.glob("*.csv")):
        df, counts = evaluate_hazards()
        assert counts["heatwave"]["train"] >= 50
        assert counts["heatwave"]["test"] >= 20
        assert counts["coldwave"]["test"] == 0
        assert counts["heavyrain"]["train"] < 50
        assert counts["heavyrain"]["test"] < 20


def test_dataset_leakage_and_splits() -> None:
    """Verify that train, embargo, and test splits have no temporal leakage."""
    pred_path = ROOT / "ml" / "extreme_event" / "reports" / "predictions_test.csv"
    assert pred_path.exists()
    test_df = pd.read_csv(pred_path)
    assert len(test_df) == 5601
    assert test_df["date"].min() >= "2024-05-01"
    assert test_df["date"].max() <= "2024-10-31"

    # If full dataset is present locally, also check train and embargo splits
    if PROCESSED_FILE.exists():
        train_df, embargo_df, _ = load_extreme_event_data()
        assert train_df["date"].max() <= "2024-04-23"
        assert embargo_df["date"].min() >= "2024-04-24"
        assert embargo_df["date"].max() <= "2024-04-30"

        # Leakage check: issue_date must strictly precede target date by lead_day
        for df in [train_df]:
            sample = df.sample(n=20, random_state=42)
            for _, row in sample.iterrows():
                target_d = dt.date.fromisoformat(row["date"])
                issue_d = dt.date.fromisoformat(row["issue_date"])
                lead = int(row["lead_day"])
                assert (target_d - issue_d).days == lead


def test_extreme_event_service_inference() -> None:
    """Verify calibrated probability, risk level, and SHAP drivers."""
    svc = ExtremeEventRiskService()

    # Scenario 1: Northern plains heatwave scenario
    res_hw = svc.predict_risk(
        lat=28.56,
        lon=77.10,
        elev=237.0,
        target_date=dt.date(2024, 5, 25),
        forecast_tmax=46.5,
    )
    assert 0.0 <= res_hw["heat_wave_risk"] <= 1.0
    assert res_hw["risk_level"] in ("low", "moderate", "high", "severe")
    assert len(res_hw["top_drivers"]) == 3
    assert res_hw["excluded_hazards"]["cold_wave"]["status"] == "excluded_feasibility_gate"
    assert res_hw["excluded_hazards"]["heavy_rain"]["status"] == "excluded_feasibility_gate"
    assert "official warning" in res_hw["advisory_note"].lower()

    # Scenario 2: High-elevation cool station (Bengaluru)
    res_cool = svc.predict_risk(
        lat=13.0,
        lon=77.5,
        elev=900.0,
        target_date=dt.date(2024, 7, 15),
        forecast_tmax=26.0,
    )
    assert res_cool["heat_wave_risk"] < 0.20
    assert res_cool["risk_level"] == "low"


@pytest.mark.asyncio
async def test_get_risk_outlook_tool_contract() -> None:
    """Verify get_risk_outlook tool produces audited risk card and disclaimers."""
    packets = await get_risk_outlook(place="Delhi", lead_day=1)
    assert isinstance(packets, list)
    assert len(packets) == 1

    pkt = packets[0]
    assert isinstance(pkt, EvidencePacket)
    assert pkt.authority_tier == 4

    vars_found = {v.variable: v.value for v in pkt.values}
    assert "heat_wave_risk" in vars_found
    assert isinstance(vars_found["heat_wave_risk"], float)
    assert "risk_level" in vars_found
    assert vars_found["risk_level"] in ("low", "moderate", "high", "severe")

    # Excluded hazards must be absent from active predictions with reasons stated
    assert vars_found.get("heavy_rain_risk") == "unavailable"
    assert "<50 train" in str(vars_found.get("heavy_rain_exclusion_reason", "")).lower()
    assert vars_found.get("cold_wave_risk") == "unavailable"
    assert "<20 test gate" in str(vars_found.get("cold_wave_exclusion_reason", "")).lower()

    # Mandatory disclaimer
    assert "official warning" in pkt.attribution.lower()
    assert "official warning" in str(vars_found.get("advisory_note", "")).lower()
