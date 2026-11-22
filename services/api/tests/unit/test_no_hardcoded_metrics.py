"""R0.2: Test that no hard-coded metrics survive in scripts/ or ml/.

This test greps source files for literal strings that the remediation plan
identified as simulated. If any are found, the test fails with the matching
lines so the offending file can be fixed.

Do NOT add exceptions for real measurements; instead, make the script read
them from a result file and write NOT MEASURED when unavailable.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]

# Directories to scan (relative to ROOT)
SCAN_DIRS = ["scripts", "ml"]

# File extensions to scan
EXTENSIONS = {".py", ".yaml", ".yml", ".json", ".md"}

# Patterns that must NOT appear as hard-coded literals.
# Each entry: (pattern, description, exclusions)
# exclusions: list of path substrings that are exempt (e.g. archived copies).
FORBIDDEN_PATTERNS: list[tuple[str, str, list[str]]] = [
    # Fake uptime from wis2_subscriber
    (r"uptime_pct\s*[=:]\s*99\.95", "hard-coded uptime 99.95%", []),
    # Fake accuracy from old model_selection
    (r"groundedness\s*=\s*99\.8", "hard-coded groundedness 99.8%", []),
    (r"groundedness\s*=\s*98\.2", "hard-coded groundedness 98.2%", []),
    (r"intent_accuracy\s*=\s*99\.0", "hard-coded intent_accuracy 99.0%", []),
    (r"intent_accuracy\s*=\s*96\.5", "hard-coded intent_accuracy 96.5%", []),
    # Fake load test results
    (r"asyncio\.sleep.*simulation", "asyncio.sleep passed off as simulation", []),
    # Hard-coded timestamp from old script
    (r'"timestamp":\s*"2026-11-17', "hard-coded benchmark timestamp", ["docs/archive"]),
    # Hard-coded alert hop from old acceptance script
    (r"12\.4 seconds", "hard-coded alert hop latency", ["docs/archive"]),
    # Hard-coded load p95 from old acceptance script
    (r"p95=32\.1 ms", "hard-coded load p95", ["docs/archive"]),
    # Hard-coded push fan-out from old acceptance script
    (r"0\.62 seconds \(simulation\)", "hard-coded push fan-out time", ["docs/archive"]),
]


def _scan_file(path: Path, pattern: re.Pattern[str], exclusions: list[str]) -> list[str]:
    path_str = path.as_posix()
    if any(ex in path_str for ex in exclusions):
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    hits = []
    for i, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            hits.append(f"{path}:{i}: {line.rstrip()}")
    return hits


@pytest.mark.parametrize("raw_pattern,description,exclusions", FORBIDDEN_PATTERNS)
def test_no_hardcoded_metric(raw_pattern: str, description: str, exclusions: list[str]) -> None:
    """Fail if the forbidden pattern is found in scripts/ or ml/ source files."""
    compiled = re.compile(raw_pattern)
    hits: list[str] = []
    for scan_dir in SCAN_DIRS:
        base = ROOT / scan_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.suffix in EXTENSIONS and path.is_file():
                hits.extend(_scan_file(path, compiled, exclusions))

    assert not hits, (
        f"Hard-coded metric found ({description}):\n" + "\n".join(hits)
    )
