#!/usr/bin/env python3
"""Run result audit and verify metrics for all models (Ticket R9.5).

verify-results = audit-results + ml verify-all
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    print("=== Step 1: Result Audit ===")
    r_audit = subprocess.run([sys.executable, str(ROOT / "scripts" / "tasks" / "audit_results.py")], cwd=str(ROOT))
    if r_audit.returncode != 0:
        print("[FAIL] Result audit failed.", file=sys.stderr)
        return r_audit.returncode

    print("\n=== Step 2: ML Model Metrics Recompute ===")
    r_ml = subprocess.run([sys.executable, str(ROOT / "scripts" / "tasks" / "ml.py"), "verify-all"], cwd=str(ROOT))
    if r_ml.returncode != 0:
        print("[FAIL] ML metrics verification failed.", file=sys.stderr)
        return r_ml.returncode

    print("\n[OK] verify-results: All audits and metric recomputations passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
