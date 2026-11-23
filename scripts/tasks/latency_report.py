from __future__ import annotations

import asyncio
import datetime as dt
import json
import statistics
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.harness import get_per_city_forecast_transport
from services.api.app.conversation.agent import ChatRequest, ConversationAgent
from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
from services.api.app.modules.forecast.service import ForecastService
from services.api.app.modules.location.adapters.open_meteo_geocoding import OpenMeteoGeocodingAdapter
from services.api.app.modules.location.resolver import LocationResolver

RESULTS_DIR = ROOT / "eval" / "results"
REPORTS_DIR = ROOT / "reports"
GOLDEN_DIR = ROOT / "eval" / "golden"

P50_BUDGET_MS = 1500
P95_BUDGET_MS = 3000


def get_git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def load_group_questions(lang: str) -> list[str]:
    """Load question strings from golden files for a given language."""
    lang_dir = GOLDEN_DIR / lang
    questions: list[str] = []
    if lang_dir.exists():
        for yml_file in sorted(lang_dir.glob("*.yaml")):
            with yml_file.open("r", encoding="utf-8") as f:
                cases = yaml.safe_load(f)
                if isinstance(cases, list):
                    for c in cases:
                        if isinstance(c, dict) and "question" in c:
                            questions.append(c["question"])
    return questions


async def measure_query_latency(agent: ConversationAgent, question: str, lang: str = "en") -> tuple[float, float]:
    """Measure Time to First Token (TTFT) and Total Duration in ms."""
    req = ChatRequest(
        session_id=f"bench_{uuid.uuid4().hex[:8]}",
        text=question,
        language=lang,
        stream=True,
    )
    t0 = time.perf_counter()
    ttft_ms = 0.0
    first_token = False
    async for event in agent.run_chat(req):
        if not first_token and event["event"] == "token":
            ttft_ms = (time.perf_counter() - t0) * 1000
            first_token = True
    total_ms = (time.perf_counter() - t0) * 1000
    if not first_token:
        ttft_ms = total_ms
    return ttft_ms, total_ms


async def run_benchmark(queries_per_group: int = 100) -> dict[str, Any]:
    # Set up offline-isolated agent backed by real per-city recorded fixtures
    transport = get_per_city_forecast_transport()
    mock_client = httpx.AsyncClient(transport=transport)
    fc_adapter = OpenMeteoForecastAdapter(client=mock_client)
    fc_service = ForecastService()
    fc_service.register_adapter(fc_adapter)

    geocoder = OpenMeteoGeocodingAdapter(client=mock_client)
    loc_resolver = LocationResolver(geocoder=geocoder)
    agent = ConversationAgent(forecast_service=fc_service, location_resolver=loc_resolver)

    # 1. English group
    en_pool = load_group_questions("en") or ["Will it rain tomorrow in Delhi?"]
    # 2. Hindi group
    hi_pool = load_group_questions("hi") or ["क्या कल दिल्ली में बारिश होगी?"]
    # 3. Regional Indic group (Bengali, Marathi, Telugu, Tamil, Odia)
    regional_pool: list[tuple[str, str]] = []
    for rlang in ["bn", "mr", "te", "ta", "or"]:
        for q in load_group_questions(rlang):
            regional_pool.append((q, rlang))

    groups: dict[str, list[tuple[str, str]]] = {
        "english": [(en_pool[i % len(en_pool)], "en") for i in range(queries_per_group)],
        "hindi": [(hi_pool[i % len(hi_pool)], "hi") for i in range(queries_per_group)],
        "indic_regional": [regional_pool[i % len(regional_pool)] for i in range(queries_per_group)],
    }

    all_ttft: list[float] = []
    all_total: list[float] = []
    group_results: dict[str, Any] = {}

    print(f"\nRunning Real Latency Benchmark: {queries_per_group} queries/group across 3 groups (Total: {queries_per_group * 3} queries)...")

    for grp_name, q_list in groups.items():
        grp_ttft: list[float] = []
        grp_total: list[float] = []
        for q_text, q_lang in q_list:
            ttft, tot = await measure_query_latency(agent, q_text, lang=q_lang)
            grp_ttft.append(ttft)
            grp_total.append(tot)
            all_ttft.append(ttft)
            all_total.append(tot)

        grp_ttft.sort()
        grp_total.sort()
        n = len(grp_ttft)

        p50_ttft = statistics.median(grp_ttft)
        p95_ttft = grp_ttft[min(int(n * 0.95), n - 1)]
        p50_total = statistics.median(grp_total)
        p95_total = grp_total[min(int(n * 0.95), n - 1)]

        group_results[grp_name] = {
            "count": n,
            "ttft_p50_ms": round(p50_ttft, 2),
            "ttft_p95_ms": round(p95_ttft, 2),
            "total_p50_ms": round(p50_total, 2),
            "total_p95_ms": round(p95_total, 2),
            "ttft_mean_ms": round(statistics.mean(grp_ttft), 2),
            "total_mean_ms": round(statistics.mean(grp_total), 2),
        }
        print(f"  Group '{grp_name}': TTFT p50={p50_ttft:.1f}ms, p95={p95_ttft:.1f}ms | Total p50={p50_total:.1f}ms, p95={p95_total:.1f}ms")

    all_ttft.sort()
    all_total.sort()
    tot_n = len(all_total)
    overall_p50_ttft = statistics.median(all_ttft)
    overall_p95_ttft = all_ttft[min(int(tot_n * 0.95), tot_n - 1)]
    overall_p50_total = statistics.median(all_total)
    overall_p95_total = all_total[min(int(tot_n * 0.95), tot_n - 1)]

    p50_pass = overall_p50_total <= P50_BUDGET_MS
    p95_pass = overall_p95_total <= P95_BUDGET_MS

    print("\n================ LATENCY REPORT ================")
    print(f"Total Measured Queries: {tot_n}")
    print(f"Overall TTFT:   p50={overall_p50_ttft:.1f} ms, p95={overall_p95_ttft:.1f} ms")
    print(f"Overall Total:  p50={overall_p50_total:.1f} ms (Budget < {P50_BUDGET_MS} ms) -> {'PASS' if p50_pass else 'FAIL'}")
    print(f"Overall Total:  p95={overall_p95_total:.1f} ms (Budget < {P95_BUDGET_MS} ms) -> {'PASS' if p95_pass else 'FAIL'}")
    print("================================================\n")

    report = {
        "git_sha": get_git_sha(),
        "measured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "provenance": "real_queries_over_recorded_fixtures",
        "total_queries": tot_n,
        "queries_per_group": queries_per_group,
        "budgets": {
            "p50_budget_ms": P50_BUDGET_MS,
            "p95_budget_ms": P95_BUDGET_MS,
        },
        "overall": {
            "ttft_p50_ms": round(overall_p50_ttft, 2),
            "ttft_p95_ms": round(overall_p95_ttft, 2),
            "total_p50_ms": round(overall_p50_total, 2),
            "total_p95_ms": round(overall_p95_total, 2),
            "p50_pass": p50_pass,
            "p95_pass": p95_pass,
        },
        "groups": group_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    for out_path in [RESULTS_DIR / "latency_report.json", REPORTS_DIR / "latency_report.json"]:
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main() -> int:
    report = asyncio.run(run_benchmark(queries_per_group=100))
    if not (report["overall"]["p50_pass"] and report["overall"]["p95_pass"]):
        print("WARNING: Latency exceeded design budget.")
        return 1
    print("latency-report: text path within design budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
