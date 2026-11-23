from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
DOCS_DIR = ROOT / "docs"
ARCHIVE_DIR = DOCS_DIR / "archive" / "unverified"


def test_unverified_artifacts_quarantined_with_banner():
    """Verify unverified evaluation artifacts are quarantined in docs/archive/unverified/ with banner (R8.1)."""
    assert ARCHIVE_DIR.exists(), "Missing docs/archive/unverified"

    eval_doc = ARCHIVE_DIR / "EVAL_RESULTS.md"
    assert eval_doc.exists(), "Missing archived EVAL_RESULTS.md in unverified archive"
    text = eval_doc.read_text(encoding="utf-8")
    assert "UNVERIFIED: produced from simulated data, do not cite" in text

    # Check 2026-11-23 and reports subdirectories in archive
    assert (ARCHIVE_DIR / "2026-11-23").exists(), "Missing archived 2026-11-23 results"
    assert (ARCHIVE_DIR / "reports").exists(), "Missing archived reports directory"


def test_no_unverified_eval_results_in_active_docs():
    """Verify docs/EVAL_RESULTS.md does not exist in active docs (R8.1)."""
    active_eval_doc = DOCS_DIR / "EVAL_RESULTS.md"
    assert not active_eval_doc.exists(), "docs/EVAL_RESULTS.md should not be in active docs while unverified"


def test_no_zero_simulated_claim_in_active_docs():
    """Verify grep for 'zero simulated' returns nothing outside the archive (R8.1)."""
    hits = []
    for p in DOCS_DIR.rglob("*.md"):
        if "archive" in p.parts:
            continue
        try:
            content = p.read_text(encoding="utf-8")
            if "zero simulated" in content.lower():
                hits.append(str(p.relative_to(ROOT)))
        except Exception:
            pass
    assert hits == [], f"Found 'zero simulated' outside archive: {hits}"


def test_proposal_deltas_contains_no_metrics():
    """Verify docs/PROPOSAL_DELTAS.md contains no performance metrics or speculative targets (R8.1)."""
    deltas_doc = DOCS_DIR / "PROPOSAL_DELTAS.md"
    assert deltas_doc.exists(), "Missing docs/PROPOSAL_DELTAS.md"
    text = deltas_doc.read_text(encoding="utf-8")

    # Bhashini and IMD keys are pending approval and were never used
    assert "Bhashini keys are pending approval and were never used" in text or "Bhashini API keys are pending approval and were never used" in text
    assert "IMD keys are pending approval and were never used" in text

    # No latency or accuracy percentage metrics
    assert not re.search(r"\b\d+\s*ms\b", text)
    assert "%" not in text
    assert "MAE" not in text
    assert "WER" not in text
    assert "speedup" not in text
    assert "zero simulated" not in text.lower()
