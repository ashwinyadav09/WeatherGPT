from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

import yaml

from services.api.app.conversation.agent import ChatRequest, ConversationAgent

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = ROOT / "eval" / "golden"
RESULTS_DIR = ROOT / "eval" / "results"


async def run_single_case(agent: ConversationAgent, case: dict[str, Any]) -> dict[str, Any]:
    req = ChatRequest(
        session_id=f"eval_{case['id']}",
        text=case["question"],
        language=case.get("language", "en"),
        stream=True,
    )

    tokens = []
    evidence_packets = []
    card = None

    async for event in agent.run_chat(req):
        evt_type = event["event"]
        data = event["data"]
        if evt_type == "token":
            tokens.append(data["text"])
        elif evt_type == "evidence":
            evidence_packets.append(data)
        elif evt_type == "card":
            card = data

    full_text = "".join(tokens)
    expect = case.get("expect", {})
    failures = []

    # Check source named
    if "source_named" in expect:
        expected_src = expect["source_named"].lower()
        if expected_src not in full_text.lower():
            failures.append(f"Expected source '{expect['source_named']}' not named in answer")

    # Check says imd not connected
    if expect.get("says_imd_not_connected"):
        if "not connected" not in full_text.lower():
            failures.append("Expected answer to mention that official IMD is not connected")

    # Check must_not
    for forbidden in expect.get("must_not", []):
        if forbidden.lower() in full_text.lower():
            failures.append(f"Forbidden word/phrase found: '{forbidden}'")

    passed = len(failures) == 0
    return {
        "id": case["id"],
        "passed": passed,
        "failures": failures,
        "answer": full_text,
        "evidence_count": len(evidence_packets),
        "has_card": card is not None,
    }


async def evaluate_language(language: str = "en") -> dict[str, Any]:
    lang_dir = GOLDEN_DIR / language
    if not lang_dir.exists():
        print(f"No golden set directory found for language '{language}' at {lang_dir}")
        return {"language": language, "total": 0, "passed": 0, "cases": []}

    cases: list[dict[str, Any]] = []
    for yml_path in lang_dir.glob("*.yaml"):
        with yml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, list):
                cases.extend(data)

    agent = ConversationAgent()
    results = []
    for c in cases:
        res = await run_single_case(agent, c)
        results.append(res)

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])

    summary = {
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
        "language": language,
        "total": total,
        "passed": passed_count,
        "accuracy": (passed_count / total) if total > 0 else 1.0,
        "cases": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_file = RESULTS_DIR / f"{dt.datetime.now(dt.timezone.utc):%Y%m%d_%H%M%S}_{language}.json"
    with report_file.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"Evaluation report written to {report_file.relative_to(ROOT)}")
    print(f"Results for '{language}': {passed_count}/{total} passed ({summary['accuracy'] * 100:.1f}%)")
    return summary
