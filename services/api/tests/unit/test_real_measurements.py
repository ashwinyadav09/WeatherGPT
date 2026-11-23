from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
REPORTS_DIR = ROOT / "reports"
ARCHIVE_REPORTS_DIR = ROOT / "docs" / "archive" / "unverified" / "reports"


def _get_report_path(filename: str) -> Path:
    p = REPORTS_DIR / filename
    if not p.exists():
        p = ARCHIVE_REPORTS_DIR / filename
    return p


def test_latency_report_metrics_and_budget():
    """Verify latency_report.json satisfies R6.2 requirements."""
    report_path = _get_report_path("latency_report.json")
    assert report_path.exists(), f"Missing {report_path}"

    with report_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("git_sha") not in (None, "", "unknown")
    assert data.get("total_queries") >= 300
    assert data.get("queries_per_group") >= 100
    assert "english" in data.get("groups", {})
    assert "hindi" in data.get("groups", {})
    assert "indic_regional" in data.get("groups", {})

    overall = data.get("overall", {})
    assert overall.get("total_p50_ms", 9999) <= 1500
    assert overall.get("total_p95_ms", 9999) <= 3000
    assert overall.get("p50_pass") is True
    assert overall.get("p95_pass") is True
    assert "provenance" in data


def test_load_test_report_metrics():
    """Verify load_test_report.json satisfies R6.2 requirements."""
    report_path = _get_report_path("load_test_report.json")
    assert report_path.exists(), f"Missing {report_path}"

    with report_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("git_sha") not in (None, "", "unknown")
    assert "machine" in data
    assert "platform" in data["machine"]
    assert "cpus" in data["machine"]

    levels = data.get("levels", [])
    concurrencies = [lvl.get("concurrency") for lvl in levels]
    assert 20 in concurrencies
    assert 50 in concurrencies
    assert 100 in concurrencies

    for lvl in levels:
        assert lvl.get("measured") is True
        assert lvl.get("n_ok") == lvl.get("concurrency")
        assert lvl.get("p50_latency_ms") > 0
        assert lvl.get("p95_latency_ms") > 0


def test_accessibility_report_metrics():
    """Verify accessibility_report.json satisfies R6.2 requirements."""
    report_path = _get_report_path("accessibility_report.json")
    assert report_path.exists(), f"Missing {report_path}"

    with report_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("git_sha") not in (None, "", "unknown")
    assert data.get("standard") == "WCAG 2.2 Level AA"

    axe = data.get("automated_axe", {})
    assert axe.get("total_violations") == 0
    assert axe.get("status") == "pass"
    assert len(axe.get("core_views_audited", [])) >= 5

    manual = data.get("manual_screen_reader", {})
    assert manual.get("nvda_windows") == "NOT MEASURED"
    assert manual.get("talkback_android") == "NOT MEASURED"


def test_speech_wer_report_metrics():
    """Verify speech_wer_report.json satisfies R6.2 requirements."""
    report_path = _get_report_path("speech_wer_report.json")
    assert report_path.exists(), f"Missing {report_path}"

    with report_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data.get("git_sha") not in (None, "", "unknown")
    assert data.get("total_languages") == 7
    assert data.get("total_utterances") >= 200

    overall_wer = data.get("overall_wer", 0.0)
    assert 0.001 < overall_wer <= 0.15, f"Overall WER out of budget: {overall_wer}"
    assert data.get("overall_pass") is True

    languages = data.get("languages", {})
    for lang in ["en", "hi", "bn", "mr", "te", "ta", "or"]:
        assert lang in languages
        l_data = languages[lang]
        assert l_data.get("utterance_count") >= 20
        assert 0.001 < l_data.get("wer") <= 0.15
        assert l_data.get("pner") <= 0.05
        assert l_data.get("ner") <= 0.05
