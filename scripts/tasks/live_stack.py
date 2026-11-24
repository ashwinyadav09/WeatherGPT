#!/usr/bin/env python3
"""Live stack and evaluation manager (Ticket R20.4).

Manages live stack (docker_http or in_process) and runs short live evaluations
with real keys and LLM/Sarvam response caching under eval/llm_cache/.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.llm_cache import (
    ProviderThrottler,
    compute_cache_key,
    get_cached_entry,
    put_cached_entry,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("live_stack")

RESULTS_DIR = ROOT / "eval" / "results"


def get_current_git_sha() -> str:
    """Return current git commit sha."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return "0" * 40


def check_api_keys() -> tuple[bool, str]:
    """Check if any real LLM or Sarvam keys are configured in environment."""
    for env_var, prov in [
        ("GROQ_API_KEY", "groq"),
        ("OPENROUTER_API_KEY", "openrouter"),
        ("SARVAM_API_KEY", "sarvam"),
    ]:
        val = os.getenv(env_var, "").strip()
        if val and not any(ph in val.lower() for ph in ("placeholder", "fake", "change-me", "your-key")):
            return True, prov
    return False, "none"


def is_docker_available() -> bool:
    """Check if docker and docker-compose are available and responsive."""
    if not shutil.which("docker"):
        return False
    try:
        proc = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def wait_for_healthz(base_url: str, timeout_seconds: int = 30) -> bool:
    """Poll /healthz until 200 OK or timeout."""
    import httpx

    health_url = f"{base_url.rstrip('/')}/healthz"
    start_sec = int(time.time())
    with httpx.Client(timeout=2) as client:
        while int(time.time()) - start_sec < timeout_seconds:
            try:
                resp = client.get(health_url)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            time.sleep(1)
    return False


class LiveStackManager:
    """Manage lifecycle of the live test stack."""

    def __init__(self, port: int = 8000, prefer_docker: bool = True) -> None:
        self.port = port
        self.prefer_docker = prefer_docker
        self.base_url = f"http://127.0.0.1:{port}"
        self.stack_type = "in_process"
        self._proc: subprocess.Popen[str] | None = None

    def start(self) -> tuple[str, str]:
        """Start stack and return (base_url, stack_type)."""
        if self.prefer_docker and is_docker_available() and (ROOT / "docker-compose.yml").exists():
            logger.info("Starting stack via Docker Compose...")
            try:
                subprocess.run(
                    ["docker", "compose", "up", "-d", "api"],
                    cwd=str(ROOT),
                    check=True,
                    capture_output=True,
                )
                if wait_for_healthz("http://localhost:8000", timeout_seconds=20):
                    self.base_url = "http://localhost:8000"
                    self.stack_type = "docker_http"
                    logger.info("Stack started in docker: %s", self.base_url)
                    return self.base_url, self.stack_type
            except Exception as exc:
                logger.warning("Docker compose startup failed (%s), falling back to in_process.", exc)

        # In-process background server
        logger.info("Starting stack in-process on port %d...", self.port)
        env = os.environ.copy()
        env["PORT"] = str(self.port)
        env["ENV"] = "test"
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "services.api.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--log-level",
            "warning",
        ]
        self._proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.stack_type = "in_process"

        if not wait_for_healthz(self.base_url, timeout_seconds=25):
            logger.warning("Healthz not responding on %s; proceeding in in_process mode.", self.base_url)
        else:
            logger.info("In-process stack ready at %s", self.base_url)

        return self.base_url, self.stack_type

    def stop(self) -> None:
        """Stop running stack."""
        if self.stack_type == "docker_http":
            try:
                subprocess.run(["docker", "compose", "stop", "api"], cwd=str(ROOT), capture_output=True)
            except Exception:
                pass
        elif self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None


def run_live_eval(live_flag: bool = False, output_file: Path | None = None) -> int:
    """Run live evaluation. Exits with NOT MEASURED without keys."""
    has_keys, provider = check_api_keys()

    if not has_keys:
        print("\n[LIVE EVALUATION] Status: NOT MEASURED")
        print("Reason: No real LLM API keys (GROQ_API_KEY, OPENROUTER_API_KEY) found in environment.")
        print("Rule T2: Not measured is a valid value. Execution stopped cleanly per Rule S1.")
        return 0

    print(f"\n[LIVE EVALUATION] Real key found for provider: {provider}. Starting live evaluation...")
    stack = LiveStackManager()
    base_url, stack_type = stack.start()
    throttler = ProviderThrottler()

    sample_cases = [
        {"id": "live-en-001", "lang": "en", "q": "What is the weather forecast for Delhi tomorrow?"},
        {"id": "live-en-002", "lang": "en", "q": "Will it rain in Mumbai tomorrow?"},
        {"id": "live-hi-001", "lang": "hi", "q": "कल दिल्ली में मौसम कैसा रहेगा?"},
        {"id": "live-hi-002", "lang": "hi", "q": "क्या कल मुंबई में बारिश होगी?"},
    ]

    import httpx

    results: list[dict[str, Any]] = []
    cases_passed = 0

    try:
        with httpx.Client(timeout=30) as client:
            for case in sample_cases:
                cache_key = compute_cache_key(
                    provider=provider,
                    model="default",
                    messages=[{"role": "user", "content": case["q"]}],
                    parameters={"language": case["lang"]},
                )

                cached = None if live_flag else get_cached_entry(cache_key)
                if cached:
                    logger.info("Cache hit for case %s (replayed: true)", case["id"])
                    ans = cached.get("response", {}).get("answer", "")
                    lat = int(cached["latency_ms"])
                    replayed = True
                else:
                    # Enforce rate limit
                    wait_ms = asyncio.run(throttler.throttle(provider))
                    if wait_ms > 0:
                        logger.info("Throttled %s for %d ms", provider, wait_ms)

                    # Real live chat call
                    t0 = time.time()
                    resp = client.post(
                        f"{base_url}/v1/chat",
                        json={"text": case["q"], "language": case["lang"], "session_id": f"live-{case['id']}"},
                    )
                    lat = int((time.time() - t0) * 1000)

                    if resp.status_code == 200:
                        data = resp.json()
                        ans = data.get("text", "")
                    else:
                        ans = f"Error: HTTP {resp.status_code}"

                    # Save to cache
                    put_cached_entry(
                        cache_key=cache_key,
                        provider=provider,
                        model="default",
                        messages=[{"role": "user", "content": case["q"]}],
                        parameters={"language": case["lang"]},
                        response={"answer": ans},
                        latency_ms=lat,
                    )
                    replayed = False

                passed = len(ans) > 0 and not ans.startswith("Error:")
                if passed:
                    cases_passed += 1

                results.append({
                    "id": case["id"],
                    "query": case["q"],
                    "language": case["lang"],
                    "latency_ms": lat,
                    "replayed": replayed,
                    "passed": passed,
                })
    finally:
        stack.stop()

    # Build audited result file
    manifest_path = ROOT / "eval" / "recordings" / "MANIFEST.json"
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest() if manifest_path.exists() else "0" * 64

    ts_str = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = output_file or (RESULTS_DIR / f"{ts_str}_live_eval.json")

    result_payload: dict[str, Any] = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generated_by": "scripts/tasks/live_stack.py",
        "git_sha": get_current_git_sha(),
        "inputs": [
            {"path": "eval/recordings/MANIFEST.json", "sha256": manifest_sha},
        ],
        "provenance": "recorded_real_http",
        "llm_path": "live",
        "stack": stack_type,
        "throttled_calls": throttler.throttled_calls,
        "total_throttle_ms": throttler.total_throttle_ms,
        "total": len(results),
        "passed": cases_passed,
        "cases": results,
    }

    out_path.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
    print(f"[OK] Live evaluation completed: {cases_passed}/{len(results)} passed.")
    print(f"Report written to {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live stack and evaluation infrastructure")
    parser.add_argument("--live", action="store_true", help="Force fresh calls, bypassing cache")
    parser.add_argument("--output", type=Path, default=None, help="Output path for eval report")
    args = parser.parse_args(argv)

    return run_live_eval(live_flag=args.live, output_file=args.output)


if __name__ == "__main__":
    sys.exit(main())
