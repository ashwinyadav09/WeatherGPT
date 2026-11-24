from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.harness import evaluate_language


def main() -> int:
    parser = argparse.ArgumentParser(description="Run golden-set evaluation")
    parser.add_argument("--lang", default="en", help="Language code (e.g. en, hi)")
    parser.add_argument("--threshold", type=float, default=0.95, help="Minimum pass rate threshold (default 0.95)")
    args = parser.parse_args()

    summary = asyncio.run(evaluate_language(language=args.lang))
    total = summary["total"]
    passed = summary["passed"]
    pass_rate = (passed / total) if total > 0 else 1.0

    if total > 0 and pass_rate < args.threshold:
        print(f"Evaluation failed: {passed}/{total} passed ({pass_rate:.1%}) below threshold {args.threshold:.1%}")
        return 1

    print(f"eval: evaluation passed ({passed}/{total}, {pass_rate:.1%}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
