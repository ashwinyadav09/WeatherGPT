from __future__ import annotations

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


def test_verified_eval_results_in_active_docs():
    """Verify docs/EVAL_RESULTS.md exists in active docs and is verified (R20.1)."""
    active_eval_doc = DOCS_DIR / "EVAL_RESULTS.md"
    assert active_eval_doc.exists(), "docs/EVAL_RESULTS.md should exist in active docs in R20.1"
    text = active_eval_doc.read_text(encoding="utf-8")
    assert "UNVERIFIED" not in text
    assert "NOT MEASURED" in text
    assert ("zero" + " simulated") not in text.lower()
    assert ("all gates" + " passed") not in text.lower()
    assert ("strictly" + " adheres") not in text.lower()


def test_no_zero_simulated_claim_in_active_docs():
    """Verify grep for banned phrases returns nothing outside the archive (R20.1)."""
    hits = []
    banned = ["zero" + " simulated", "strictly" + " adheres", "all" + " gates passed"]
    for p in DOCS_DIR.rglob("*.md"):
        if "archive" in p.parts:
            continue
        try:
            content = p.read_text(encoding="utf-8")
            for phrase in banned:
                if phrase in content.lower():
                    hits.append(f"{p.relative_to(ROOT)}: {phrase}")
        except Exception:
            pass
    assert hits == [], f"Found banned phrases outside archive: {hits}"


def test_proposal_deltas_audited_metrics():
    """Verify docs/PROPOSAL_DELTAS.md reflects audited results and truthfulness (R19)."""
    deltas_doc = DOCS_DIR / "PROPOSAL_DELTAS.md"
    assert deltas_doc.exists(), "Missing docs/PROPOSAL_DELTAS.md"
    text = deltas_doc.read_text(encoding="utf-8")

    # Bhashini and IMD keys are pending approval and were never used
    assert "Bhashini keys are pending approval and were never used" in text or "Bhashini API keys are pending approval and were never used" in text
    assert "IMD keys are pending approval and were never used" in text

    # Proposal objectives tracked with targets, measured values and what changed
    assert "Proposal Target" in text or "target" in text.lower()
    assert "Measured Value" in text or "measured" in text.lower()
    assert "NOT MEASURED" in text
    assert ("zero" + " simulated") not in text.lower()
