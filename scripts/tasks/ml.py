#!/usr/bin/env python3
"""Machine learning CLI tasks (Ticket R9.3, R9.5).

Subcommands:
  ml verify <model>     Recompute headline metrics for a model and verify against metrics.json
  ml verify-all         Verify metrics for all models in ml/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.common.recompute import verify_model_metrics


def cmd_verify(model_name: str) -> int:
    model_dir = ROOT / "ml" / model_name
    if not model_dir.exists():
        print(f"[FAIL] Model directory ml/{model_name} does not exist.", file=sys.stderr)
        return 1

    try:
        result = verify_model_metrics(model_dir, root_dir=ROOT)
        if result["status"] == "not_trained":
            print(f"[INFO] ml verify {model_name}: {result['message']}")
            return 0
        print(f"[OK] ml verify {model_name}: n_test={result['n_test']}, metrics: {result['verified_metrics']}")
        return 0
    except Exception as exc:
        print(f"[FAIL] ml verify {model_name}: {exc}", file=sys.stderr)
        return 1


def cmd_verify_all() -> int:
    ml_dir = ROOT / "ml"
    models = [d.name for d in ml_dir.iterdir() if d.is_dir() and d.name not in ("common", "__pycache__")]
    if not models:
        print("[INFO] No models found in ml/ to verify.")
        return 0

    failed = 0
    verified = 0
    for m in models:
        code = cmd_verify(m)
        if code != 0:
            failed += 1
        else:
            verified += 1

    if failed:
        print(f"\n[FAIL] {failed} model(s) failed verification.", file=sys.stderr)
        return 1
    print(f"\n[OK] All {verified} model(s) verified.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ml.py", description="WeatherGPT ML tasks")
    sub = parser.add_subparsers(dest="action", required=True)

    v_parser = sub.add_parser("verify", help="verify model metrics against predictions_test.csv")
    v_parser.add_argument("model", nargs="?", default=None, help="Name of model directory in ml/")

    sub.add_parser("verify-all", help="verify all models in ml/")

    args = parser.parse_args(argv)

    if args.action == "verify":
        if not args.model:
            return cmd_verify_all()
        return cmd_verify(args.model)
    elif args.action == "verify-all":
        return cmd_verify_all()

    return 0


if __name__ == "__main__":
    sys.exit(main())
