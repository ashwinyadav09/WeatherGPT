from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.app.conversation.agent import ChatRequest, ConversationAgent

RESULTS_DIR = ROOT / "eval" / "results"
P50_BUDGET_MS = 1500
P95_BUDGET_MS = 3000

SAMPLE_QUESTIONS = [
    "Will it rain tomorrow in Pune?",
    "Is it going to rain tomorrow in Mumbai?",
    "Any rain expected in Delhi tomorrow?",
    "Do I need an umbrella in Bengaluru tomorrow?",
    "Tomorrow rain forecast for Chennai",
    "Will there be rainfall in Kolkata tomorrow?",
    "Will it rain in Hyderabad tomorrow?",
    "Is rain predicted for Ahmedabad tomorrow?",
    "Rain tomorrow in Jaipur?",
    "Will Lucknow see rain tomorrow?",
]


async def measure_query_latency(agent: ConversationAgent, question: str) -> float:
    req = ChatRequest(
        session_id="benchmark_session",
        text=question,
        language="en",
        stream=True,
    )
    t0 = time.perf_counter()
    async for _ in agent.run_chat(req):
        pass
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return elapsed_ms


async def run_benchmark(iterations: int = 20) -> dict[str, float | int | str]:
    import httpx

    from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
    from services.api.app.modules.forecast.service import ForecastService

    fixture_path = ROOT / "eval" / "fixtures" / "open_meteo" / "pune_forecast.json"
    if fixture_path.exists():
        with fixture_path.open("r", encoding="utf-8") as f:
            fix_data = json.load(f)
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=fix_data))
        mock_client = httpx.AsyncClient(transport=transport)
        fc_adapter = OpenMeteoForecastAdapter(client=mock_client)
        fc_service = ForecastService()
        fc_service.register_adapter(fc_adapter)
        agent = ConversationAgent(forecast_service=fc_service)
    else:
        agent = ConversationAgent()

    latencies: list[float] = []

    print(f"Running latency benchmark ({iterations} runs)...")
    for i in range(iterations):
        q = SAMPLE_QUESTIONS[i % len(SAMPLE_QUESTIONS)]
        lat = await measure_query_latency(agent, q)
        latencies.append(lat)

    latencies.sort()
    p50 = statistics.median(latencies)
    p90 = latencies[int(len(latencies) * 0.90)]
    p95 = latencies[int(len(latencies) * 0.95)]
    min_lat = min(latencies)
    max_lat = max(latencies)
    avg_lat = statistics.mean(latencies)

    print("\n================ LATENCY REPORT ================")
    print(f"Total Requests: {len(latencies)}")
    print(f"p50 Latency:    {p50:.1f} ms  (Budget: < {P50_BUDGET_MS} ms) -> {'PASS' if p50 <= P50_BUDGET_MS else 'FAIL'}")
    print(f"p90 Latency:    {p90:.1f} ms")
    print(f"p95 Latency:    {p95:.1f} ms  (Budget: < {P95_BUDGET_MS} ms) -> {'PASS' if p95 <= P95_BUDGET_MS else 'FAIL'}")
    print(f"Min Latency:    {min_lat:.1f} ms")
    print(f"Max Latency:    {max_lat:.1f} ms")
    print(f"Mean Latency:   {avg_lat:.1f} ms")
    print("================================================\n")

    report = {
        "iterations": len(latencies),
        "p50_ms": round(p50, 1),
        "p90_ms": round(p90, 1),
        "p95_ms": round(p95, 1),
        "min_ms": round(min_lat, 1),
        "max_ms": round(max_lat, 1),
        "mean_ms": round(avg_lat, 1),
        "p50_budget_ms": P50_BUDGET_MS,
        "p95_budget_ms": P95_BUDGET_MS,
        "p50_pass": p50 <= P50_BUDGET_MS,
        "p95_pass": p95 <= P95_BUDGET_MS,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = RESULTS_DIR / "latency_report.json"
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


def main() -> int:
    report = asyncio.run(run_benchmark())
    if not (report["p50_pass"] and report["p95_pass"]):
        print("WARNING: Latency exceeded design budget.")
        return 1
    print("latency-report: text path within design budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
