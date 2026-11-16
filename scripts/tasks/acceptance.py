from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def run_sub(cmd: list[str]) -> bool:
    res = subprocess.run([sys.executable, *cmd], cwd=str(ROOT))
    return res.returncode == 0


def main() -> int:
    gates = [
        ("Secret scan", ["scripts/dev.py", "secret-scan"]),
        ("Single migration head", ["scripts/tasks/db_heads.py"]),
        ("Contracts & OpenAPI validation", ["scripts/tasks/contracts.py"]),
        ("Seam and unit test suites", ["scripts/tasks/test.py"]),
        ("Golden-set evaluation (en)", ["scripts/tasks/eval.py", "--lang", "en"]),
    ]

    print("\n================== ACCEPTANCE GATES ==================")
    results = []
    all_passed = True
    for name, cmd in gates:
        print(f"\nEvaluating gate: {name}")
        passed = run_sub(cmd)
        results.append((name, passed))
        if not passed:
            all_passed = False

    print("\n=================== SUMMARY TABLE ===================")
    print(f"{'Gate':<35} | {'Result':<10}")
    print("-" * 48)
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        print(f"{name:<35} | {status:<10}")

    if all_passed:
        print("\nAll acceptance gates passed successfully.")
        return 0
    else:
        print("\nSome acceptance gates failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
