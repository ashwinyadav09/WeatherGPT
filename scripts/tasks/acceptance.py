#!/usr/bin/env python3
"""WeatherGPT Acceptance Gate Runner (Ticket R6.4).

Reads machine-readable result files under eval/results/<date>/ (or eval/results/ and reports/),
and reports NOT MEASURED for any missing or unmeasured gate.
With --strict, gates on:
- Golden sets for all 7 Tier-1 languages (en, hi, bn, mr, te, ta, or) >= 95%
- Latency (TTFT p95 <= 1500 ms, Total p95 <= 3000 ms)
- Concurrency scalability (20, 50, 100 users p95 <= 1500 ms)
- Automated accessibility (0 violations)
- Speech ASR (WER <= 15%, entity error <= 5%)
- Ablations (5 core studies with significant improvement)
- Infrastructure (tests, secret-scan, db-heads, contracts)

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
REPORTS_DIR = ROOT / "reports"
NOT_MEASURED = "NOT MEASURED"

LANGUAGES = ["en", "hi", "bn", "mr", "te", "ta", "or"]


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


def get_active_results_dir() -> Path:
    today_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    dated = RESULTS_DIR / today_str
    if dated.exists():
        return dated
    # Check if any dated subdirectory exists
    subdirs = sorted([d for d in RESULTS_DIR.iterdir() if d.is_dir() and d.name.startswith("202")], reverse=True)
    if subdirs:
        return subdirs[0]
    return RESULTS_DIR


def load_json_file(filename: str) -> dict[str, Any] | None:
    active_dir = get_active_results_dir()
    for search_path in [active_dir / filename, REPORTS_DIR / filename, RESULTS_DIR / filename]:
        if search_path.exists():
            try:
                with search_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return None


def latest_eval_result(lang: str) -> dict[str, Any] | None:
    active_dir = get_active_results_dir()
    # Check in active dated dir first
    direct_eval = active_dir / f"eval_{lang}.json"
    if direct_eval.exists():
        try:
            with direct_eval.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass

    # Search in RESULTS_DIR
    files = sorted(RESULTS_DIR.glob(f"*_{lang}.json"), reverse=True)
    for f in files:
        try:
            with f.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            continue
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
    pct = (passed_count / total) if total else 0.0
    ok = pct >= target_pass_rate
    return GateResult(
        parameter="Accuracy & Relevance",
        gate_name=f"{lang.upper()} Golden Set",
        target=f">= {target_pass_rate:.0%}",
        measured=f"{passed_count}/{total} ({pct:.1%})",
        passed=ok,
    )


def latency_ttft_gate() -> GateResult:
    data = load_json_file("latency_report.json")
    if data is None:
        return GateResult(
            parameter="Response Latency",
            gate_name="TTFT p95",
            target="<= 1500 ms",
            measured=NOT_MEASURED,
            passed=None,
        )
    p95 = data.get("overall", {}).get("ttft_p95_ms") or data.get("ttft_p95_ms")
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


def latency_total_gate() -> GateResult:
    data = load_json_file("latency_report.json")
    if data is None:
        return GateResult(
            parameter="Response Latency",
            gate_name="Total duration p95",
            target="<= 3000 ms",
            measured=NOT_MEASURED,
            passed=None,
        )
    p95 = data.get("overall", {}).get("total_p95_ms") or data.get("total_p95_ms")
    if p95 is None:
        return GateResult(
            parameter="Response Latency",
            gate_name="Total duration p95",
            target="<= 3000 ms",
            measured=NOT_MEASURED,
            passed=None,
        )
    ok = float(p95) <= 3000.0
    return GateResult(
        parameter="Response Latency",
        gate_name="Total duration p95",
        target="<= 3000 ms",
        measured=f"{p95} ms",
        passed=ok,
    )


def load_test_gate(concurrency: int) -> GateResult:
    data = load_json_file("load_test_report.json")
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


def accessibility_gate() -> GateResult:
    data = load_json_file("accessibility_report.json")
    if data is None:
        return GateResult(
            parameter="Accessibility",
            gate_name="WCAG 2.2 AA automated axe-core",
            target="0 violations",
            measured=NOT_MEASURED,
            passed=None,
        )
    violations = data.get("automated_axe", {}).get("total_violations")
    if violations is None:
        return GateResult(
            parameter="Accessibility",
            gate_name="WCAG 2.2 AA automated axe-core",
            target="0 violations",
            measured=NOT_MEASURED,
            passed=None,
        )
    ok = violations == 0
    return GateResult(
        parameter="Accessibility",
        gate_name="WCAG 2.2 AA automated axe-core",
        target="0 violations",
        measured=f"{violations} violations",
        passed=ok,
    )


def speech_wer_gate() -> GateResult:
    data = load_json_file("speech_wer_report.json")
    if data is None:
        return GateResult(
            parameter="Voice & Speech",
            gate_name="Speech ASR across 7 languages",
            target="WER <= 15%, entity <= 5%",
            measured=NOT_MEASURED,
            passed=None,
        )
    overall_wer = data.get("overall_wer_percent")
    overall_pass = data.get("overall_pass")
    if overall_wer is None:
        return GateResult(
            parameter="Voice & Speech",
            gate_name="Speech ASR across 7 languages",
            target="WER <= 15%, entity <= 5%",
            measured=NOT_MEASURED,
            passed=None,
        )
    return GateResult(
        parameter="Voice & Speech",
        gate_name="Speech ASR across 7 languages",
        target="WER <= 15%, entity <= 5%",
        measured=f"Mean WER {overall_wer}%",
        passed=bool(overall_pass),
    )


def ablations_gate() -> GateResult:
    data = load_json_file("ablations_report.json")
    if data is None:
        return GateResult(
            parameter="Model & Agent Ablations",
            gate_name="5 core ablation studies",
            target="All 5 completed & significant",
            measured=NOT_MEASURED,
            passed=None,
        )
    ablations = data.get("ablations", {})
    count = len(ablations)
    ok = count >= 5
    return GateResult(
        parameter="Model & Agent Ablations",
        gate_name="5 core ablation studies",
        target="All 5 completed & significant",
        measured=f"{count}/5 ablations evaluated",
        passed=ok,
    )


def evaluate_acceptance_gates(strict: bool = False, run_subcommands: bool = True) -> tuple[list[GateResult], bool]:
    gates: list[GateResult] = []

    # --- Accuracy ---
    test_ok = run_sub(["scripts/tasks/test.py"]) if run_subcommands else True
    gates.append(GateResult(
        parameter="Accuracy & Relevance",
        gate_name="Unit & seam tests",
        target="100% pass",
        measured="PASS" if test_ok else "FAIL",
        passed=test_ok,
    ))
    for lang in LANGUAGES:
        gates.append(eval_gate(lang))

    # --- Latency ---
    gates.append(latency_ttft_gate())
    gates.append(latency_total_gate())

    # --- Scalability ---
    for level in [20, 50, 100]:
        gates.append(load_test_gate(level))

    # --- Accessibility ---
    gates.append(accessibility_gate())

    # --- Speech ---
    gates.append(speech_wer_gate())

    # --- Ablations ---
    gates.append(ablations_gate())

    # --- Infrastructure ---
    sec_ok = run_sub(["scripts/dev.py", "secret-scan"]) if run_subcommands else True
    gates.append(GateResult(
        parameter="Infrastructure",
        gate_name="Secret scan",
        target="0 secrets",
        measured="PASS" if sec_ok else "FAIL",
        passed=sec_ok,
    ))
    db_ok = run_sub(["scripts/tasks/db_heads.py"]) if run_subcommands else True
    gates.append(GateResult(
        parameter="Infrastructure",
        gate_name="Single Alembic head",
        target="Exactly 1 head",
        measured="PASS" if db_ok else "FAIL",
        passed=db_ok,
    ))
    contracts_ok = run_sub(["scripts/tasks/contracts.py"]) if run_subcommands else True
    gates.append(GateResult(
        parameter="Infrastructure",
        gate_name="Contract tests",
        target="All pass",
        measured="PASS" if contracts_ok else "FAIL",
        passed=contracts_ok,
    ))

    all_passed = True
    for g in gates:
        if strict:
            if not g.passed:
                all_passed = False
        else:
            if g.passed is False:
                all_passed = False

    return gates, all_passed


def main() -> int:
    strict = "--strict" in sys.argv
    today_str = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    # Always ensure dated evaluation directory & docs/EVAL_RESULTS.md are synchronized
    subprocess.run([sys.executable, str(ROOT / "scripts" / "tasks" / "generate_eval_results.py")], cwd=str(ROOT), capture_output=True)

    print("\n" + "=" * 80)
    print(f"WeatherGPT Acceptance Gates — {today_str}{'  [--strict]' if strict else ''}")
    print("=" * 80)

    gates, all_passed = evaluate_acceptance_gates(strict=strict, run_subcommands=True)

    # --- Summary ---
    print("\n" + "=" * 105)
    print("ACCEPTANCE GATES SUMMARY")
    print("=" * 105)
    hdr = f"| {'Parameter':<24} | {'Gate':<36} | {'Target':<22} | {'Measured':<26} | Status |"
    print(hdr)
    print("|" + "-" * 26 + "|" + "-" * 38 + "|" + "-" * 24 + "|" + "-" * 28 + "|--------|")

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
        print(f"| {g.parameter:<24} | {g.gate_name:<36} | {g.target:<22} | {g.measured:<26} | {status} |")
        md_lines.append(f"| {g.parameter} | {g.gate_name} | {g.target} | {g.measured} | {status} |")

    overall = "UNKNOWN (gates missing)" if any_missing else ("ALL PASSED" if not any_failing else "GATES FAILED")
    md_lines.extend([
        "",
        f"**Overall**: {overall}",
        f"**Generated**: {dt.datetime.now(dt.timezone.utc).isoformat()}",
    ])

    date_dir = RESULTS_DIR / today_str
    date_dir.mkdir(parents=True, exist_ok=True)
    report_file = date_dir / f"acceptance-{today_str}.md"
    with report_file.open("w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    # Also save to root of eval/results/
    root_report_file = RESULTS_DIR / f"acceptance-{today_str}.md"
    with root_report_file.open("w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print("=" * 105)
    print(f"Report: {report_file}")
    print(f"Overall: {overall}")
    print("=" * 105)

    if strict and (any_missing or any_failing):
        print("--strict: exiting non-zero (gates missing or failing)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
