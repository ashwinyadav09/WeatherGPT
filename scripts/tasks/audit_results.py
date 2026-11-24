#!/usr/bin/env python3
"""Audit result files under ml/*/reports/ and eval/results/** (Ticket R9.2).

Enforces Rule T1-T8 (no-simulated-results.md):
- generated_by: points to an existing script
- git_sha: present in git history
- inputs[].sha256: matches the file on disk
- provenance: in allowed list (live_api, recorded_real_http, real_audio, human_labels, fixture_test_only)
- performance claims never use fixture_test_only
- latency or load results require llm_path in ('live', 'disabled'), never 'stub'
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_PROVENANCES = {
    "live_api",
    "recorded_real_http",
    "real_audio",
    "human_labels",
    "fixture_test_only",
}

PERFORMANCE_METRICS = {
    "accuracy",
    "f1",
    "macro_f1",
    "weighted_f1",
    "mae",
    "rmse",
    "wer",
    "p95",
    "latency_p50",
    "latency_p95",
    "p50_ms",
    "p95_ms",
    "ttft_p95",
    "total_p95",
}

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _is_git_commit(git_sha: str, root_dir: Path = ROOT) -> bool:
    """Verify that a git sha exists in git history."""
    if not git_sha or not isinstance(git_sha, str):
        return False
    try:
        proc = subprocess.run(
            ["git", "cat-file", "-e", f"{git_sha}^{{commit}}"],
            cwd=str(root_dir),
            capture_output=True,
        )
        return proc.returncode == 0
    except Exception:
        return False


def audit_result_data(data: dict[str, Any], file_path: Path, root_dir: Path = ROOT) -> list[str]:
    """Audit parsed JSON data against all R9.2 truthfulness rules."""
    errors: list[str] = []
    rel_path = str(file_path.relative_to(root_dir)) if file_path.is_relative_to(root_dir) else str(file_path)

    # 1. generated_by
    generated_by = data.get("generated_by")
    if not generated_by or not isinstance(generated_by, str):
        errors.append(f"{rel_path}: Missing or invalid 'generated_by' field")
    else:
        gen_script = root_dir / generated_by
        if not gen_script.exists():
            errors.append(f"{rel_path}: 'generated_by' script does not exist on disk: {generated_by}")

    # 2. git_sha
    git_sha = data.get("git_sha")
    if not git_sha or not isinstance(git_sha, str):
        errors.append(f"{rel_path}: Missing or invalid 'git_sha' field")
    elif not _is_git_commit(git_sha, root_dir=root_dir):
        errors.append(f"{rel_path}: 'git_sha' ({git_sha}) not found in git commit history")

    # 3. inputs[].sha256
    inputs = data.get("inputs")
    if inputs is None or not isinstance(inputs, list):
        errors.append(f"{rel_path}: Missing or invalid 'inputs' list")
    else:
        for idx, item in enumerate(inputs):
            if not isinstance(item, dict):
                errors.append(f"{rel_path}: inputs[{idx}] is not an object")
                continue
            sha = item.get("sha256")
            if not sha or not SHA256_RE.match(sha):
                errors.append(f"{rel_path}: inputs[{idx}] missing or invalid sha256: {sha}")
                continue
            input_path_str = item.get("path")
            if input_path_str:
                disk_file = root_dir / input_path_str
                if disk_file.exists():
                    computed_sha = hashlib.sha256(disk_file.read_bytes()).hexdigest()
                    if computed_sha.lower() != sha.lower():
                        errors.append(
                            f"{rel_path}: inputs[{idx}].sha256 mismatch for '{input_path_str}': expected {sha}, got {computed_sha}"
                        )

    # 4. provenance
    prov = data.get("provenance")
    if not prov or prov not in ALLOWED_PROVENANCES:
        errors.append(f"{rel_path}: Invalid provenance '{prov}'. Allowed: {sorted(ALLOWED_PROVENANCES)}")

    # 5. No fixture_test_only in performance claims
    has_perf_metrics = any(k in data for k in PERFORMANCE_METRICS)
    if has_perf_metrics and prov == "fixture_test_only":
        errors.append(
            f"{rel_path}: 'fixture_test_only' provenance forbidden in performance claims (Rule T6)"
        )

    # 6. Latency / Load results require llm_path in ('live', 'disabled')
    is_latency_or_load = (
        "latency" in file_path.name.lower()
        or "load" in file_path.name.lower()
        or any(k in data for k in ("ttft_p95", "total_p95", "latency_ms", "ttft_ms"))
    )
    if is_latency_or_load:
        llm_path = data.get("llm_path")
        if llm_path not in ("live", "disabled"):
            errors.append(
                f"{rel_path}: Latency/load results require 'llm_path' in ('live', 'disabled'), got: {llm_path!r} (never 'stub')"
            )

    # 7. Ablation / comparison results require per-case CSV in inputs
    is_ablation_or_comparison = (
        "ablation" in file_path.name.lower()
        or "comparison" in file_path.name.lower()
        or "ablations" in data
        or "comparisons" in data
    )
    if is_ablation_or_comparison:
        has_csv_input = any(
            isinstance(item, dict) and str(item.get("path", "")).lower().endswith(".csv")
            for item in (inputs if isinstance(inputs, list) else [])
        )
        if not has_csv_input:
            errors.append(
                f"{rel_path}: Ablation/comparison results must contain a per-case file (CSV) referenced in inputs (Rule R20.2 #7)"
            )

    # 8. Reject degenerate intervals (ci_lower == ci_upper) unless explicit degenerate_reason
    def _check_degenerate(obj: Any, prefix: str = "") -> list[str]:
        errs: list[str] = []
        if isinstance(obj, dict):
            if "ci_lower" in obj and "ci_upper" in obj:
                cl = obj["ci_lower"]
                cu = obj["ci_upper"]
                if isinstance(cl, (int, float)) and isinstance(cu, (int, float)):
                    if cl == cu:
                        if "degenerate_reason" not in obj and "degenerate_reason" not in data:
                            errs.append(
                                f"{rel_path}: Degenerate confidence interval ({prefix}ci_lower == ci_upper == {cl}) without explicit 'degenerate_reason' (Rule R20.2 #8)"
                            )
            for k, v in obj.items():
                errs.extend(_check_degenerate(v, f"{prefix}{k}."))
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                errs.extend(_check_degenerate(item, f"{prefix}[{idx}]."))
        return errs

    errors.extend(_check_degenerate(data))

    # 9. Truthful llm_path for product quality / latency
    if prov in ("recorded_real_http", "live_api") and data.get("llm_path") == "disabled":
        claims_product_quality_or_latency = (
            any(k in data for k in ("accuracy", "grounding_pass_rate", "faithfulness", "quality", "ttft_p95", "total_p95", "latency_ms", "ttft_ms"))
            or "latency" in file_path.name.lower()
            or "ablation" in file_path.name.lower()
        )
        if claims_product_quality_or_latency:
            errors.append(
                f"{rel_path}: Results with provenance '{prov}' cannot claim to measure product quality/latency with llm_path: disabled (Rule N5 / R20.2 #9)"
            )

    # 10. Significant flag must match interval excluding zero
    def _check_significant(obj: Any, prefix: str = "") -> list[str]:
        errs: list[str] = []
        if isinstance(obj, dict):
            if "significant" in obj:
                sig = obj["significant"]
                if "ci_lower" in obj and "ci_upper" in obj:
                    cl = obj["ci_lower"]
                    cu = obj["ci_upper"]
                    if isinstance(cl, (int, float)) and isinstance(cu, (int, float)):
                        interval_excludes_zero = (cl > 0 and cu > 0) or (cl < 0 and cu < 0)
                        if sig != interval_excludes_zero:
                            errs.append(
                                f"{rel_path}: 'significant': {sig} at {prefix} does not match interval [{cl}, {cu}] (interval excludes zero: {interval_excludes_zero}) (Rule R20.2 #10)"
                            )
            for k, v in obj.items():
                errs.extend(_check_significant(v, f"{prefix}{k}."))
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                errs.extend(_check_significant(item, f"{prefix}[{idx}]."))
        return errs

    errors.extend(_check_significant(data))

    return errors


def audit_json_file(file_path: Path, root_dir: Path = ROOT) -> list[str]:
    """Load and audit a single JSON file."""
    rel_path = str(file_path.relative_to(root_dir)) if file_path.is_relative_to(root_dir) else str(file_path)
    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception as exc:
        return [f"{rel_path}: Failed to read/parse JSON: {exc}"]

    if not isinstance(data, dict):
        return [f"{rel_path}: Top-level JSON must be an object/dict"]

    return audit_result_data(data, file_path, root_dir=root_dir)


def find_result_files(root_dir: Path = ROOT) -> list[Path]:
    """Find all result JSON files in ml/*/reports/ and eval/results/**."""
    targets: list[Path] = []
    # 1. ml/*/reports/**/*.json
    for p in (root_dir / "ml").glob("*/reports/**/*.json"):
        if p.is_file():
            targets.append(p)
    # 2. eval/results/**/*.json
    eval_results_dir = root_dir / "eval" / "results"
    if eval_results_dir.exists():
        for p in eval_results_dir.rglob("*.json"):
            if p.is_file():
                targets.append(p)
    return sorted(targets)


BANNED_N6_PHRASES = [
    "zero " + "".join(["s", "i", "m", "u", "l", "a", "t", "e", "d"]),
    "all " + "gates passed",
    "strictly " + "adheres",
]


def scan_docs_for_banned_phrases(root_dir: Path = ROOT) -> list[str]:
    """Scan docs/** (except archive) and .scratch/weathergpt/progress/** for Rule N6 banned phrases."""
    errors: list[str] = []
    targets: list[Path] = []
    docs_dir = root_dir / "docs"
    if docs_dir.exists():
        for p in docs_dir.rglob("*.md"):
            if "archive" not in p.parts:
                targets.append(p)
    progress_dir = root_dir / ".scratch" / "weathergpt" / "progress"
    if progress_dir.exists():
        for p in progress_dir.rglob("*.md"):
            targets.append(p)

    for path in targets:
        try:
            content = path.read_text(encoding="utf-8", errors="replace").lower()
            for phrase in BANNED_N6_PHRASES:
                if phrase in content:
                    rel_p = str(path.relative_to(root_dir)) if path.is_relative_to(root_dir) else str(path)
                    errors.append(f"{rel_p}: Contains banned self-certification phrase '{phrase}' (Rule N6 / R20.2 #11)")
        except Exception as exc:
            errors.append(f"{path}: ReadError: {exc}")
    return errors


def audit_all_results(files: list[Path] | None = None, root_dir: Path = ROOT) -> list[str]:
    """Audit all result files, returning any errors found."""
    target_files = files if files is not None else find_result_files(root_dir=root_dir)
    all_errors: list[str] = []
    for f in target_files:
        errors = audit_json_file(f, root_dir=root_dir)
        all_errors.extend(errors)
    # Docs scan for Rule N6
    docs_errors = scan_docs_for_banned_phrases(root_dir=root_dir)
    all_errors.extend(docs_errors)
    return all_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit result JSON files under ml/*/reports and eval/results")
    parser.add_argument("files", nargs="*", help="Optional specific JSON files to audit")
    args = parser.parse_args(argv)

    if args.files:
        targets = [Path(f).resolve() for f in args.files]
    else:
        targets = find_result_files()

    print(f"audit-results: auditing {len(targets)} result file(s)...")
    errors = audit_all_results(targets)

    if errors:
        print(f"\n[FAIL] Audit failed with {len(errors)} violation(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"[OK] audit-results: all {len(targets)} result file(s) passed audit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
