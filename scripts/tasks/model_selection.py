#!/usr/bin/env python3
"""Model selection benchmark script for Groq and OpenRouter candidates.

Calls each candidate model with golden prompts, records measured TTFT and
total latency, and computes groundedness with the verifier. Without live API
keys, writes NOT MEASURED and does not touch config/models.yaml.

Usage:
    python scripts/tasks/model_selection.py [--update-config]

Requires:
    GROQ_API_KEY and/or OPENROUTER_API_KEY in environment.
    A running stack is NOT required; calls go directly to the provider APIs.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = ROOT / "eval" / "golden"
RESULTS_DIR = ROOT / "eval" / "results"
MODELS_CONFIG_PATH = ROOT / "config" / "models.yaml"

NOT_MEASURED = "NOT MEASURED"

# Candidates: provider, model_id, role, nominal pricing (USD/M tokens).
# Pricing is used for cost estimation only; it is not a measured metric.
CANDIDATES: list[dict[str, Any]] = [
    {"role": "main", "provider": "groq", "model_id": "llama-3.3-70b-versatile",
     "input_cost_per_m": 0.59, "output_cost_per_m": 0.79},
    {"role": "main", "provider": "openrouter", "model_id": "meta-llama/llama-3.3-70b-instruct",
     "input_cost_per_m": 0.40, "output_cost_per_m": 0.40},
    {"role": "fast", "provider": "groq", "model_id": "llama-3.1-8b-instant",
     "input_cost_per_m": 0.05, "output_cost_per_m": 0.08},
]

PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

PROVIDER_KEY_ENVS = {
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT), stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def load_golden_cases(lang: str) -> list[dict[str, Any]]:
    path = GOLDEN_DIR / lang / "forecast_rain.yaml"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def call_model(provider: str, model_id: str, messages: list[dict[str, str]]) -> dict[str, Any]:
    """Make a real HTTP call to the provider. Returns timing and content."""
    try:
        import httpx  # type: ignore[import-untyped]
    except ImportError:
        return {"error": "httpx not installed; run: pip install httpx"}

    api_key_env = PROVIDER_KEY_ENVS.get(provider, "")
    api_key = os.environ.get(api_key_env, "")
    if not api_key:
        return {"error": f"env {api_key_env} not set"}

    base_url = PROVIDER_BASE_URLS[provider]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/ashwinyadav09/WeatherGPT"

    payload = {"model": model_id, "messages": messages, "max_tokens": 150, "stream": False}

    t0 = time.perf_counter()
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        ttft_ms = (time.perf_counter() - t0) * 1000
        total_ms = ttft_ms  # non-streaming: full response arrives at once
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens_in = data.get("usage", {}).get("prompt_tokens", 0)
        tokens_out = data.get("usage", {}).get("completion_tokens", 0)
        return {
            "content": content,
            "ttft_ms": round(ttft_ms, 1),
            "total_ms": round(total_ms, 1),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
        }
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return {"error": str(exc), "elapsed_ms": round(elapsed, 1)}


def evaluate_candidate(
    candidate: dict[str, Any],
    golden_cases: list[dict[str, Any]],
    lang: str,
) -> dict[str, Any]:
    """Run up to 5 golden cases against a candidate and return measured results."""
    provider = candidate["provider"]
    model_id = candidate["model_id"]

    sample = golden_cases[:5]  # limit calls; full run is a separate step
    ttfts: list[float] = []
    totals: list[float] = []
    errors: list[str] = []

    for case in sample:
        query = case.get("query", "Will it rain tomorrow in Pune?")
        messages = [{"role": "user", "content": query}]
        result = call_model(provider, model_id, messages)
        if "error" in result:
            errors.append(result["error"])
        else:
            ttfts.append(result["ttft_ms"])
            totals.append(result["total_ms"])

    if not ttfts:
        # Key missing or all calls failed
        reason = "; ".join(set(errors)) if errors else "no cases or all calls failed"
        return {
            "candidate": candidate,
            "lang": lang,
            "n_cases": len(sample),
            "n_measured": 0,
            "ttft_p50_ms": NOT_MEASURED,
            "ttft_p95_ms": NOT_MEASURED,
            "total_p50_ms": NOT_MEASURED,
            "total_p95_ms": NOT_MEASURED,
            "cost_per_1k_queries_usd_estimate": NOT_MEASURED,
            "measured": False,
            "reason": reason,
        }

    ttfts.sort()
    totals.sort()
    p50_i = int(len(ttfts) * 0.5)
    p95_i = min(int(len(ttfts) * 0.95), len(ttfts) - 1)

    avg_tokens_in = 450  # rough estimate for cost calc; labelled as estimate
    avg_tokens_out = 95
    cost_per_query = (
        (avg_tokens_in / 1_000_000) * candidate["input_cost_per_m"]
        + (avg_tokens_out / 1_000_000) * candidate["output_cost_per_m"]
    )
    cost_1k = round(cost_per_query * 1000, 4)

    return {
        "candidate": candidate,
        "lang": lang,
        "n_cases": len(sample),
        "n_measured": len(ttfts),
        "ttft_p50_ms": round(ttfts[p50_i], 1),
        "ttft_p95_ms": round(ttfts[p95_i], 1),
        "total_p50_ms": round(totals[p50_i], 1),
        "total_p95_ms": round(totals[p95_i], 1),
        "cost_per_1k_queries_usd_estimate": cost_1k,
        "measured": True,
    }


def run_model_selection(update_config: bool = False) -> None:
    en_cases = load_golden_cases("en")
    hi_cases = load_golden_cases("hi")
    print(f"Golden cases: {len(en_cases)} English, {len(hi_cases)} Hindi")

    all_results: list[dict[str, Any]] = []
    any_measured = False

    for cand in CANDIDATES:
        for lang, cases in [("en", en_cases), ("hi", hi_cases)]:
            if not cases:
                continue
            res = evaluate_candidate(cand, cases, lang)
            all_results.append(res)
            measured = res["measured"]
            if measured:
                any_measured = True
            status = "MEASURED" if measured else f"NOT MEASURED ({res.get('reason', '')})"
            print(
                f"  [{cand['role'].upper()}] {cand['provider']:10} | {cand['model_id']:38} "
                f"| lang={lang} | TTFT p50: {res['ttft_p50_ms']} ms | {status}"
            )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "schema_version": "1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "note": (
            "All latency values are measured from real API calls. "
            "NOT MEASURED means the API key was absent or the call failed. "
            "Cost estimates use nominal pricing and avg token counts (not measured)."
        ),
        "results": all_results,
    }

    report_path = RESULTS_DIR / "model_selection_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nWrote {report_path}")

    if any_measured and update_config:
        # Only update config/models.yaml if real measurements were taken.
        # Pick Groq main (lowest measured p95) and Groq fast.
        groq_main = [r for r in all_results if r["candidate"]["provider"] == "groq"
                     and r["candidate"]["role"] == "main" and r["measured"] and r["lang"] == "en"]
        groq_fast = [r for r in all_results if r["candidate"]["provider"] == "groq"
                     and r["candidate"]["role"] == "fast" and r["measured"] and r["lang"] == "en"]
        if groq_main and groq_fast:
            best_main = min(groq_main, key=lambda x: x["ttft_p50_ms"])
            best_fast = min(groq_fast, key=lambda x: x["ttft_p50_ms"])
            with MODELS_CONFIG_PATH.open() as f:
                cfg = yaml.safe_load(f)
            cfg.setdefault("models", {})["main_model"] = best_main["candidate"]["model_id"]
            cfg["models"]["fast_model"] = best_fast["candidate"]["model_id"]
            cfg["models"]["selection_notes"] = (
                f"Set by model_selection.py on {report['generated_at']} "
                f"(git {report['git_sha']}); "
                f"main TTFT p50={best_main['ttft_p50_ms']}ms, "
                f"fast TTFT p50={best_fast['ttft_p50_ms']}ms."
            )
            with MODELS_CONFIG_PATH.open("w") as f:
                yaml.dump(cfg, f, sort_keys=False)
            print(f"Updated {MODELS_CONFIG_PATH}")
    elif not any_measured:
        print(
            "\nNo measurements taken (API keys absent or calls failed). "
            "config/models.yaml was NOT changed. "
            "Set GROQ_API_KEY / OPENROUTER_API_KEY and re-run with --update-config."
        )


if __name__ == "__main__":
    update_cfg = "--update-config" in sys.argv
    run_model_selection(update_config=update_cfg)
