#!/usr/bin/env python3
"""Machine learning CLI tasks (Ticket R9.3, R9.5, R11).

Subcommands:
  ml download <model>   Download real training and verification data for model
  ml train <model>      Train model artifacts on real data
  ml eval <model>       Evaluate model on held-out test block and render MODEL_CARD.md
  ml verify <model>     Recompute headline metrics for a model and verify against metrics.json
  ml verify-all         Verify metrics for all models in ml/
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.common.recompute import verify_model_metrics


def _run_submodule_action(model_name: str, action: str) -> int:
    """Run an action (download, train, eval) for a model."""
    script_path = ROOT / "ml" / model_name / f"{action}.py"
    if not script_path.exists():
        print(f"[FAIL] Action script not found: {script_path.relative_to(ROOT)}", file=sys.stderr)
        return 1

    proc = subprocess.run([sys.executable, str(script_path)], cwd=str(ROOT))
    return proc.returncode


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

    # download
    d_parser = sub.add_parser("download", help="download real data for model")
    d_parser.add_argument("model", help="Name of model directory in ml/")

    # train
    t_parser = sub.add_parser("train", help="train model artifacts on real data")
    t_parser.add_argument("model", help="Name of model directory in ml/")

    # eval
    e_parser = sub.add_parser("eval", help="evaluate model on held-out test block")
    e_parser.add_argument("model", help="Name of model directory in ml/")

    # verify
    v_parser = sub.add_parser("verify", help="verify model metrics against predictions_test.csv")
    v_parser.add_argument("model", nargs="?", default=None, help="Name of model directory in ml/")

    # verify-all
    sub.add_parser("verify-all", help="verify all models in ml/")

    args = parser.parse_args(argv)

    if args.action == "download":
        return _run_submodule_action(args.model, "download")
    elif args.action == "train":
        return _run_submodule_action(args.model, "train")
    elif args.action == "eval":
        return _run_submodule_action(args.model, "eval")
    elif args.action == "verify":
        if not args.model:
            return cmd_verify_all()
        return cmd_verify(args.model)
    elif args.action == "verify-all":
        return cmd_verify_all()

    return 0


if __name__ == "__main__":
    sys.exit(main())
