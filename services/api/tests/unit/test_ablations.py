from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
REPORTS_DIR = ROOT / "reports"


def test_ablations_report_structure_and_ci():
    """Verify ablations_report.json satisfies Ticket R6.3 requirements."""
    report_path = REPORTS_DIR / "ablations_report.json"
    assert report_path.exists(), f"Missing {report_path}"

    with report_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("git_sha") not in (None, "", "unknown")
    assert data.get("bootstrap_samples") >= 1000
    assert data.get("confidence_level") == 0.95
    assert "ablations" in data

    ablations = data["ablations"]
    assert "no_tools_vs_tools" in ablations
    assert "tools_vs_tools_plus_rag" in ablations
    assert "raw_nwp_vs_ridge_vs_lightgbm" in ablations
    assert "encoder_vs_llm_intent" in ablations
    assert "cascaded_vs_native_hindi" in ablations

    # 1. No tools vs Tools
    a1 = ablations["no_tools_vs_tools"]
    assert a1["no_tools"]["ci_lower"] <= a1["no_tools"]["mean"] <= a1["no_tools"]["ci_upper"]
    assert a1["tools"]["ci_lower"] <= a1["tools"]["mean"] <= a1["tools"]["ci_upper"]
    assert a1["tools"]["mean"] > a1["no_tools"]["mean"]
    assert a1["delta"]["significant"] is True

    # 2. Tools vs Tools + RAG
    a2 = ablations["tools_vs_tools_plus_rag"]
    assert a2["tools_only"]["ci_lower"] <= a2["tools_only"]["mean"] <= a2["tools_only"]["ci_upper"]
    assert a2["tools_plus_rag"]["ci_lower"] <= a2["tools_plus_rag"]["mean"] <= a2["tools_plus_rag"]["ci_upper"]
    assert a2["tools_plus_rag"]["mean"] > a2["tools_only"]["mean"]
    assert a2["delta"]["significant"] is True

    # 3. Raw NWP vs Ridge vs LightGBM (Improvement excludes zero)
    a3 = ablations["raw_nwp_vs_ridge_vs_lightgbm"]
    assert a3["raw_nwp"]["mean"] > a3["ridge_mos"]["mean"]
    improvements = a3["improvements"]
    assert improvements["ridge_over_raw"]["mae_reduction"] > 0
    assert improvements["ridge_over_raw"]["ci_lower"] > 0, "Gate: improvement interval must exclude zero"
    assert improvements["ridge_over_raw"]["significant"] is True
    assert improvements["lightgbm_over_raw"]["ci_lower"] > 0
    assert improvements["lightgbm_over_raw"]["significant"] is True

    # 4. Encoder vs LLM Intent
    a4 = ablations["encoder_vs_llm_intent"]
    assert a4["encoder"]["accuracy"]["ci_lower"] <= a4["encoder"]["accuracy"]["mean"] <= a4["encoder"]["accuracy"]["ci_upper"]
    assert a4["speedup_factor"] > 10.0, "Encoder must be significantly faster than LLM function calling"

    # 5. Cascaded Translation vs Native Hindi
    a5 = ablations["cascaded_vs_native_hindi"]
    assert a5["cascaded_translation"]["mean"] == 1.0
    assert a5["delta"]["significant"] is True
    assert a5["delta"]["ci_lower"] > 0
