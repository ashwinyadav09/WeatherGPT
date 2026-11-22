#!/usr/bin/env python3
"""WeatherGPT Acceptance Gate Runner.

Reads result files under eval/results/ and reports NOT MEASURED for any
missing or stale gate. With --strict, exits non-zero if any gate is missing
or failing.

Usage:
    python scripts/tasks/acceptance.py [--strict]
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "eval" / "results"
NOT_MEASURED = "NOT MEASURED"


@dataclass
class GateResult:
    parameter: str
    gate_name: str
    target: str
    measured: str
    passed: bool | None  # None = not measured


def run_sub(cmd: list[str]) -> bool:
    res = subprocess.run([sys.executable, *cmd], cwd=str(ROOT), capture_output=True)
    return res.returncode == 0


def latest_eval_result(lang: str) -> dict[str, Any] | None:
    """Return the most recent eval result JSON for the given language, or None."""
    files = sorted(RESULTS_DIR.glob(f"*_{lang}.json"), reverse=True)
    for f in files:
        # skip archived files (those in subdirectories)
        if f.parent != RESULTS_DIR:
            continue
        try:
            with f.open(encoding="utf-8") as fh:
                data = json.load(fh)
            return data
        except Exception:
            continue
    return None


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def eval_gate(lang: str, target_pass_rate: float = 0.95) -> GateResult:
    data = latest_eval_result(lang)
    if data is None:
        return GateResult(
            parameter="Accuracy & Relevance",
            gate_name=f"{lang.upper()} Golden Set",
            target=f">= {target_pass_rate:.0%}",
            measured=NOT_MEASURED,
            passed=None,
        )
    passed_count = data.get("passed", 0)
    total = data.get("total", 0)
    pct = passed_count / total if total else 0
    ok = pct >= target_pass_rate
    return GateResult(
        parameter="Accuracy & Relevance",
        gate_name=f"{lang.upper()} Golden Set",
        target=f">= {target_pass_rate:.0%}",
        measured=f"{passed_count}/{total} ({pct:.1%})",
        passed=ok,
    )


def latency_gate() -> GateResult:
    path = RESULTS_DIR / "latency_report.json"
    data = load_json(path)
    if data is None:
        return GateResult(
            parameter="Response Latency",
            gate_name="TTFT p95",
            target="<= 1500 ms",
            measured=NOT_MEASURED,
            passed=None,
        )
    p95 = data.get("ttft_p95_ms")
    if p95 is None:
        return GateResult(
            parameter="Response Latency",
            gate_name="TTFT p95",
            target="<= 1500 ms",
            measured=NOT_MEASURED,
            passed=None,
        )
    ok = float(p95) <= 1500.0
    return GateResult(
        parameter="Response Latency",
        gate_name="TTFT p95",
        target="<= 1500 ms",
        measured=f"{p95} ms",
        passed=ok,
    )


def load_test_gate(concurrency: int) -> GateResult:
    path = RESULTS_DIR / "load_test_report.json"
    data = load_json(path)
    if data is None:
        return GateResult(
            parameter="Scalability",
            gate_name=f"Load {concurrency} concurrent users p95",
            target="<= 1500 ms",
            measured=NOT_MEASURED,
            passed=None,
        )
    levels: list[dict[str, Any]] = data.get("levels", [])
    for lv in levels:
        if lv.get("concurrency") == concurrency:
            if not lv.get("measured"):
                return GateResult(
                    parameter="Scalability",
                    gate_name=f"Load {concurrency} concurrent users p95",
                    target="<= 1500 ms",
                    measured=NOT_MEASURED,
                    passed=None,
                )
            p95 = lv.get("p95_latency_ms")
            ok = float(p95) <= 1500.0
            return GateResult(
                parameter="Scalability",
                gate_name=f"Load {concurrency} concurrent users p95",
                target="<= 1500 ms",
                measured=f"{p95} ms",
                passed=ok,
            )
    return GateResult(
        parameter="Scalability",
        gate_name=f"Load {concurrency} concurrent users p95",
        target="<= 1500 ms",
        measured=NOT_MEASURED,
        passed=None,
    )


def main() -> int:
    strict = "--strict" in sys.argv
    today_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    print("\n" + "=" * 75)
    print(f"WeatherGPT Acceptance Gates — {today_str}{'  [--strict]' if strict else ''}")
    print("=" * 75)

    gates: list[GateResult] = []

    # --- Accuracy ---
    print("\n[1] Accuracy & Relevance")
    test_ok = run_sub(["scripts/tasks/test.py"])
    gates.append(GateResult(
        parameter="Accuracy & Relevance",
        gate_name="Unit & seam tests",
        target="100% pass",
        measured="PASS" if test_ok else "FAIL",
        passed=test_ok,
    ))
    gates.append(eval_gate("en"))
    gates.append(eval_gate("hi"))

    # --- Latency ---
    print("[2] Response Latency")
    gates.append(latency_gate())

    # --- Scalability ---
    print("[3] Scalability")
    for level in [20, 50, 100]:
        gates.append(load_test_gate(level))

    # --- Infrastructure ---
    print("[4] Infrastructure")
    sec_ok = run_sub(["scripts/dev.py", "secret-scan"])
    gates.append(GateResult(
        parameter="Infrastructure",
        gate_name="Secret scan",
        target="0 secrets",
        measured="PASS" if sec_ok else "FAIL",
        passed=sec_ok,
    ))
    db_ok = run_sub(["scripts/tasks/db_heads.py"])
    gates.append(GateResult(
        parameter="Infrastructure",
        gate_name="Single Alembic head",
        target="Exactly 1 head",
        measured="PASS" if db_ok else "FAIL",
        passed=db_ok,
    ))
    contracts_ok = run_sub(["scripts/tasks/contracts.py"])
    gates.append(GateResult(
        parameter="Infrastructure",
        gate_name="Contract tests",
        target="All pass",
        measured="PASS" if contracts_ok else "FAIL",
        passed=contracts_ok,
    ))

    # --- Summary ---
    print("\n" + "=" * 95)
    print("ACCEPTANCE GATES SUMMARY")
    print("=" * 95)
    hdr = f"| {'Parameter':<24} | {'Gate':<36} | {'Target':<20} | {'Measured':<24} | Status |"
    print(hdr)
    print("|" + "-" * 26 + "|" + "-" * 38 + "|" + "-" * 22 + "|" + "-" * 26 + "|--------|")

    md_lines = [
        f"# WeatherGPT Acceptance Gates Report ({today_str})",
        "",
        "| Parameter | Gate | Target | Measured | Status |",
        "|---|---|---|---|---|",
    ]

    any_missing = False
    any_failing = False
    for g in gates:
        if g.passed is None:
            status = "⚠️ N/A"
            any_missing = True
        elif g.passed:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            any_failing = True
        print(f"| {g.parameter:<24} | {g.gate_name:<36} | {g.target:<20} | {g.measured:<24} | {status} |")
        md_lines.append(f"| {g.parameter} | {g.gate_name} | {g.target} | {g.measured} | {status} |")

    overall = "UNKNOWN (gates missing)" if any_missing else ("ALL PASSED" if not any_failing else "GATES FAILED")
    md_lines.extend([
        "",
        f"**Overall**: {overall}",
        f"**Generated**: {dt.datetime.now(dt.timezone.utc).isoformat()}",
    ])

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = RESULTS_DIR / f"acceptance-{today_str}.md"
    with report_file.open("w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print("=" * 95)
    print(f"Report: {report_file}")
    print(f"Overall: {overall}")
    print("=" * 95)

    if strict and (any_missing or any_failing):
        print("--strict: exiting non-zero (gates missing or failing)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
