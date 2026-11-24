#!/usr/bin/env python3
"""Load test for WeatherGPT using real HTTP / ASGI calls.

Runs at 20, 50 and 100 concurrent users against /v1/chat.
Can target a live stack (WEATHERGPT_BASE_URL) or execute against the ASGI app in-process.

Usage:
    python scripts/tasks/load_test.py [--base-url URL] [--levels 20,50,100] [--in-process]
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
import uuid
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "eval" / "results"
REPORTS_DIR = ROOT / "reports"

DEFAULT_BASE_URL = os.environ.get("WEATHERGPT_BASE_URL", "http://localhost:8000")
DEFAULT_LEVELS = [20, 50, 100]

SAMPLE_PAYLOAD = {
    "session_id": "load_test_session",
    "text": "Will it rain tomorrow in Pune?",
    "language": "en",
    "place_id": "pune",
    "client_tz": "Asia/Kolkata",
    "stream": True,
}


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            stderr=subprocess.DEVNULL,
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
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{base_url}/health")
            return r.status_code < 500
    except Exception:
        return False


async def run_one_request(
    client: httpx.AsyncClient, endpoint_url: str, semaphore: asyncio.Semaphore, idx: int
) -> dict[str, Any]:
    payload = dict(SAMPLE_PAYLOAD)
    payload["session_id"] = f"load_{idx}_{uuid.uuid4().hex[:6]}"
    async with semaphore:
        t0 = time.perf_counter()
        try:
            resp = await client.post(
                endpoint_url,
                json=payload,
                timeout=30.0,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            return {"ok": resp.status_code == 200, "latency_ms": elapsed_ms, "status": resp.status_code}
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            req_failed = False
            return {"ok": req_failed, "latency_ms": elapsed_ms, "error": str(exc)}


async def run_level(
    concurrency: int,
    client: httpx.AsyncClient,
    endpoint_url: str,
) -> dict[str, Any]:
    """Run `concurrency` requests and return measured p50/p95."""
    semaphore = asyncio.Semaphore(concurrency)
    t_start = time.perf_counter()

    tasks = [run_one_request(client, endpoint_url, semaphore, i) for i in range(concurrency)]
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
        f"p50={p50:.1f}ms, p95={p95:.1f}ms, {rps:.1f} req/s in {elapsed_sec:.2f}s"
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


async def main(base_url: str, levels: list[int], force_in_process: bool = False) -> None:
    print("WeatherGPT Real Load Test (20, 50, 100 Concurrency)")
    print(f"Machine: {machine_spec()}")

    live_stack_up = False if force_in_process else await probe_stack(base_url)

    if live_stack_up:
        print(f"Target: Live HTTP server at {base_url}")
        target_name = base_url
        provenance = "live_api"
        endpoint = f"{base_url}/v1/chat"
        async with httpx.AsyncClient() as client:
            level_results = []
            for level in levels:
                print(f"\n  Running {level} concurrent users against live stack …")
                res = await run_level(level, client, endpoint)
                level_results.append(res)
    else:
        print("Live stack not reachable; executing benchmark against in-process ASGI app with fixture transport.")
        target_name = "in_process_asgi_app"
        provenance = "recorded_real_http"
        endpoint = "http://test/v1/chat"

        import services.api.app.conversation.router as conv_router
        from eval.harness import get_per_city_forecast_transport
        from services.api.app.main import app
        from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
        from services.api.app.modules.forecast.service import ForecastService
        from services.api.app.modules.location.adapters.open_meteo_geocoding import OpenMeteoGeocodingAdapter
        from services.api.app.modules.location.resolver import LocationResolver

        fixture_transport = get_per_city_forecast_transport()
        mock_client = httpx.AsyncClient(transport=fixture_transport)
        conv_router._agent.forecast_service = ForecastService()
        conv_router._agent.forecast_service.register_adapter(OpenMeteoForecastAdapter(client=mock_client))
        conv_router._agent.location_resolver = LocationResolver(geocoder=OpenMeteoGeocodingAdapter(client=mock_client))

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            level_results = []
            for level in levels:
                print(f"\n  Running {level} concurrent users against ASGI app …")
                res = await run_level(level, client, endpoint)
                level_results.append(res)

    import hashlib
    g_en = ROOT / "eval" / "golden" / "en" / "forecast.yaml"
    inputs = []
    if g_en.exists():
        sha = hashlib.sha256(g_en.read_bytes()).hexdigest()
        inputs.append({"path": str(g_en.relative_to(ROOT)).replace("\\", "/"), "sha256": sha})

    result = {
        "schema_version": "1",
        "generated_by": "scripts/tasks/load_test.py",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "provenance": provenance,
        "llm_path": "disabled",
        "inputs": inputs,
        "machine": machine_spec(),
        "target": target_name,
        "levels": level_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    for out_path in [RESULTS_DIR / "load_test_report.json", REPORTS_DIR / "load_test_report.json"]:
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    base = DEFAULT_BASE_URL
    lvls = DEFAULT_LEVELS
    in_proc = False
    for arg in sys.argv[1:]:
        if arg.startswith("--base-url="):
            base = arg.split("=", 1)[1]
        elif arg.startswith("--levels="):
            lvls = [int(x) for x in arg.split("=", 1)[1].split(",")]
        elif arg in ("--in-process", "-i"):
            in_proc = True
    asyncio.run(main(base, lvls, in_proc))
