from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DOCS_DIR = ROOT / "docs"


def test_proposal_deltas_document():
    """Verify docs/PROPOSAL_DELTAS.md exists and covers all 5 key deltas."""
    deltas_doc = DOCS_DIR / "PROPOSAL_DELTAS.md"
    assert deltas_doc.exists(), "Missing docs/PROPOSAL_DELTAS.md"

    text = deltas_doc.read_text(encoding="utf-8")
    # 1. IMD replaced by SACHET
    assert "SACHET" in text and "IMD" in text
    assert "IMD_ENABLED" in text
    # 2. Bhashini replaced by Sarvam
    assert "Bhashini" in text and "Sarvam" in text
    # 3. Targets re-confirmed against measured baselines
    assert "Truthfulness" in text or "baselines" in text
    # 4. Voice optional
    assert "Voice" in text and "optional" in text.lower()
    # 5. Aviation not supported
    assert "Aviation" in text and ("not supported" in text.lower() or "deprecated" in text.lower())

    assert "SIMULATED" not in text
    assert "{{" not in text


def test_aligned_documentation_files():
    """Verify README.md and docs/{architecture,ml-plan,eval-and-acceptance}.md are aligned."""
    readme = ROOT / "README.md"
    arch = DOCS_DIR / "architecture.md"
    ml_plan = DOCS_DIR / "ml-plan.md"
    eval_acc = DOCS_DIR / "eval-and-acceptance.md"

    for doc in [readme, arch, ml_plan, eval_acc]:
        assert doc.exists(), f"Missing {doc.name}"
        text = doc.read_text(encoding="utf-8")
        assert "{{" not in text, f"Unresolved template in {doc.name}"
        assert "SIMULATED" not in text, f"Simulated claims found in {doc.name}"

    # Check specific mentions
    readme_text = readme.read_text(encoding="utf-8")
    assert "NDMA SACHET" in readme_text
    assert "Open-Meteo" in readme_text
    assert "PROPOSAL_DELTAS.md" in readme_text

    ml_plan_text = ml_plan.read_text(encoding="utf-8")
    assert "PointForecastMOSModel" in ml_plan_text or "Point-Forecast Bias Correction" in ml_plan_text
    assert "Intent Classification" in ml_plan_text
    assert "Advisory RAG" in ml_plan_text

    eval_text = eval_acc.read_text(encoding="utf-8")
    assert "The 19 Acceptance Gates" in eval_text or "19 automated acceptance gates" in eval_text


@pytest.mark.asyncio
async def test_demo_script_execution():
    """Verify demo script runs without exceptions."""
    from scripts.tasks.demo import (
        step_2_trace_panel,
        step_3_ml_on_off,
        step_4_risk_card,
        step_5_climate_trend,
        step_6_rag_advice,
        step_7_alert_relay,
        step_8_eval_and_acceptance,
    )

    # Test trace panel display
    await step_2_trace_panel({})

    # Test ML on/off
    await step_3_ml_on_off()

    # Test Risk card
    await step_4_risk_card()

    # Test Climate trend
    await step_5_climate_trend()

    # Test RAG advice
    await step_6_rag_advice()

    # Test Alert relay
    await step_7_alert_relay()

    # Test Evals & acceptance table
    await step_8_eval_and_acceptance()
