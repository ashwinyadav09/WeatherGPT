#!/usr/bin/env python3
"""Load test for WeatherGPT using real HTTP calls against the local stack.

Runs at 20, 50 and 100 concurrent users against /v1/chat.
Requires the stack to be running (python scripts/dev.py up).

Usage:
    python scripts/tasks/load_test.py [--base-url URL] [--levels 20,50,100]

If the stack is not reachable the report records NOT MEASURED and exits 0
(so CI still passes; use acceptance --strict to gate on this).
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "eval" / "results"

NOT_MEASURED = "NOT MEASURED"

DEFAULT_BASE_URL = os.environ.get("WEATHERGPT_BASE_URL", "http://localhost:8000")
DEFAULT_LEVELS = [20, 50, 100]

SAMPLE_PAYLOAD = {
    "query": "Will it rain tomorrow in Pune?",
    "place_id": "pune",
    "lang": "en",
}


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT), stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def machine_spec() -> dict[str, str]:
    return {
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "python": platform.python_version(),
        "cpus": str(os.cpu_count()),
    }


async def probe_stack(base_url: str) -> bool:
    """Return True if the stack responds to /health."""
    try:
        import httpx  # type: ignore[import-untyped]
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base_url}/health")
            return r.status_code < 500
    except Exception:
        return False


async def run_one_request(
    client: Any, base_url: str, semaphore: asyncio.Semaphore
) -> dict[str, Any]:
    async with semaphore:
        t0 = time.perf_counter()
        try:
            resp = await client.post(
                f"{base_url}/v1/chat",
                json=SAMPLE_PAYLOAD,
                timeout=30.0,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return {"ok": resp.status_code < 400, "latency_ms": elapsed_ms, "status": resp.status_code}
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return {"ok": False, "latency_ms": elapsed_ms, "error": str(exc)}


async def run_level(base_url: str, concurrency: int) -> dict[str, Any]:
    """Run `concurrency` requests and return measured p50/p95."""
    try:
        import httpx  # type: ignore[import-untyped]
    except ImportError:
        return {"concurrency": concurrency, "measured": False, "reason": "httpx not installed"}

    semaphore = asyncio.Semaphore(concurrency)
    t_start = time.perf_counter()

    async with httpx.AsyncClient() as client:
        tasks = [run_one_request(client, base_url, semaphore) for _ in range(concurrency)]
        outcomes = await asyncio.gather(*tasks)

    elapsed_sec = time.perf_counter() - t_start
    latencies = sorted(r["latency_ms"] for r in outcomes)
    n = len(latencies)
    ok_count = sum(1 for r in outcomes if r["ok"])

    p50 = latencies[int(n * 0.50)] if n else 0
    p95 = latencies[min(int(n * 0.95), n - 1)] if n else 0

    rps = concurrency / elapsed_sec if elapsed_sec > 0 else 0

    print(
        f"  concurrency={concurrency}: {ok_count}/{concurrency} ok, "
        f"p50={p50:.0f}ms, p95={p95:.0f}ms, {rps:.1f} req/s in {elapsed_sec:.1f}s"
    )

    return {
        "concurrency": concurrency,
        "n_requests": concurrency,
        "n_ok": ok_count,
        "elapsed_sec": round(elapsed_sec, 2),
        "requests_per_second": round(rps, 1),
        "p50_latency_ms": round(p50, 1),
        "p95_latency_ms": round(p95, 1),
        "measured": True,
    }


async def main(base_url: str, levels: list[int]) -> None:
    print(f"WeatherGPT load test  —  target: {base_url}")
    print(f"Machine: {machine_spec()}")

    stack_up = await probe_stack(base_url)
    if not stack_up:
        print(f"\nStack not reachable at {base_url}. Run 'python scripts/dev.py up' first.")
        result = {
            "schema_version": "1",
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "git_sha": git_sha(),
            "machine": machine_spec(),
            "base_url": base_url,
            "levels": [
                {"concurrency": c, "measured": False, "reason": "stack not reachable"}
                for c in levels
            ],
        }
    else:
        level_results = []
        for level in levels:
            print(f"\n  Running {level} concurrent users …")
            res = await run_level(base_url, level)
            level_results.append(res)

        result = {
            "schema_version": "1",
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "git_sha": git_sha(),
            "machine": machine_spec(),
            "base_url": base_url,
            "levels": level_results,
        }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = RESULTS_DIR / "load_test_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nWrote {report_path}")


if __name__ == "__main__":
    base = DEFAULT_BASE_URL
    lvls = DEFAULT_LEVELS
    for arg in sys.argv[1:]:
        if arg.startswith("--base-url="):
            base = arg.split("=", 1)[1]
        elif arg.startswith("--levels="):
            lvls = [int(x) for x in arg.split("=", 1)[1].split(",")]
    asyncio.run(main(base, lvls))
