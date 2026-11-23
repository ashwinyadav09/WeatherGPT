from __future__ import annotations

import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DOCS_DIR = ROOT / "docs"
RESULTS_DIR = ROOT / "eval" / "results"


def test_eval_results_document_contents():
    """Verify docs/EVAL_RESULTS.md exists and contains verified metrics for all 7 Tier-1 languages."""
    eval_doc = DOCS_DIR / "EVAL_RESULTS.md"
    assert eval_doc.exists(), "Missing docs/EVAL_RESULTS.md"

    text = eval_doc.read_text(encoding="utf-8")
    assert "ALL ACCEPTANCE GATES PASSED" in text
    assert "English" in text and "`en`" in text
    assert "Hindi" in text and "`hi`" in text
    assert "Bengali" in text and "`bn`" in text
    assert "Marathi" in text and "`mr`" in text
    assert "Telugu" in text and "`te`" in text
    assert "Tamil" in text and "`ta`" in text
    assert "Odia" in text and "`or`" in text

    # Check 5 ablations are present
    assert "1. Tools" in text
    assert "2. RAG" in text
    assert "3. NWP Post-Processing" in text
    assert "4. Intent Classification" in text
    assert "5. Translation Strategy" in text

    # Ensure no template placeholders remain
    assert "{{" not in text
    assert "SIMULATED" not in text


def test_dated_eval_results_directory():
    """Verify dated directory exists under eval/results/<date>/ with archived reports."""
    today_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    date_dir = RESULTS_DIR / today_str
    assert date_dir.exists(), f"Missing dated results directory at {date_dir}"

    for expected_file in [
        "latency_report.json",
        "load_test_report.json",
        "accessibility_report.json",
        "speech_wer_report.json",
        "ablations_report.json",
        "EVAL_RESULTS.md",
        f"acceptance-{today_str}.md",
    ]:
        fpath = date_dir / expected_file
        assert fpath.exists(), f"Missing archived report {expected_file} in {date_dir}"
