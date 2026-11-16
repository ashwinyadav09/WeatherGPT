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
    args = parser.parse_args()

    summary = asyncio.run(evaluate_language(language=args.lang))
    if summary["total"] > 0 and summary["passed"] < summary["total"]:
        print(f"Evaluation failed: {summary['total'] - summary['passed']} failures")
        return 1

    print("eval: evaluation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
