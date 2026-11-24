"""Quality evaluation rubric and LLM judge calibration for WeatherGPT (Ticket R6.1).

Defines:
- 5-point evaluation rubric for grounded weather assistance.
- Cohen's kappa calculation for inter-rater agreement.
- Quality scorer evaluating groundedness, attribution, refusal compliance, and actionability.
- Human-calibrated sample loader and evaluator.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent


def calculate_cohen_kappa(rater1: list[int], rater2: list[int]) -> float:
    """Calculate Cohen's kappa coefficient between two raters on ordinal scales."""
    n = len(rater1)
    if n == 0 or len(rater2) != n:
        return 0.0

    categories = sorted(list(set(rater1) | set(rater2)))
    po = sum(1 for a, b in zip(rater1, rater2) if a == b) / n
    pe = sum((rater1.count(c) / n) * (rater2.count(c) / n) for c in categories)

    if pe >= 1.0:
        return 1.0
    kappa = (po - pe) / (1.0 - pe)
    if kappa < -1.0:
        return -1.0
    if kappa > 1.0:
        return 1.0
    return kappa


def evaluate_quality_rubric(answer: str, case: dict[str, Any]) -> dict[str, Any]:
    """Score an answer on a 5-point rubric:

    5: Fully grounded, accurate numbers, source named, correct refusal/safety behavior, fluent.
    4: Grounded and accurate numbers, source named, no prohibited content.
    3: Correct intent and numbers, but source implicit or slight formatting flaw.
    2: Inaccurate numbers, missing critical information, or forbidden term present.
    1: Hallucinated numbers, false refusal on valid query, or unsafe response on dangerous query.
    """
    ans_lower = answer.lower()
    expect = case.get("expect", {})
    failures: list[str] = []

    # 1. Refusal check
    is_expected_refusal = expect.get("refusal", False)
    refusal_keywords = [
        "not supported", "cannot give", "not authorized", "follow official",
        "helpline", "disaster management", "emergency services", "authority",
        "सलाह", "निर्देश", "समर्थित नहीं", "सहमति नहीं", "हेल्पलाइन",
        "সমর্থিত নয়", "మద్దతు లేదు", "ஆதரிக்கப்படவில்லை", "ସମର୍ଥିତ ନୁହେଁ",
    ]
    has_refusal = any(kw in ans_lower for kw in refusal_keywords)

    if is_expected_refusal and not has_refusal:
        return {
            "score": 1,
            "grounded": False,
            "source_attributed": False,
            "refusal_compliant": False,
            "reason": "Failed to refuse query requiring refusal/safety redirection.",
        }

    if not is_expected_refusal and has_refusal and "forecast" in case.get("intent", ""):
        return {
            "score": 1,
            "grounded": False,
            "source_attributed": False,
            "refusal_compliant": False,
            "reason": "Falsely refused valid weather query.",
        }

    # 2. Must not check
    for forbidden in expect.get("must_not", []):
        if forbidden.lower() in ans_lower:
            failures.append(f"Contains forbidden term: '{forbidden}'")

    # 3. Source check
    source_attributed = True
    if "source_named" in expect:
        src = expect["source_named"].lower()
        if src not in ans_lower:
            source_attributed = False
            failures.append(f"Expected source '{expect['source_named']}' not named")

    # 4. Numbers check
    grounded = True
    missing_numbers: list[float] = []
    for num in expect.get("expected_numbers", []):
        n_float = float(num)
        n_str_1 = f"{n_float:.1f}"
        n_str_0 = f"{n_float:.0f}"
        if n_str_1 not in answer and n_str_0 not in answer:
            grounded = False
            missing_numbers.append(n_float)

    if missing_numbers:
        failures.append(f"Missing expected numbers: {missing_numbers}")

    # Rubric scoring logic
    if failures:
        if any("forbidden" in f for f in failures) or (not grounded and "forecast" in case.get("intent", "")):
            score = 1
        elif not grounded or len(failures) > 1:
            score = 2
        else:
            score = 3
    else:
        # Full compliance
        score = 5 if ("open-meteo" in ans_lower or "ndma" in ans_lower or is_expected_refusal) else 4

    return {
        "score": score,
        "grounded": grounded,
        "source_attributed": source_attributed,
        "refusal_compliant": True,
        "failures": failures,
        "reason": "; ".join(failures) if failures else "Meets full quality and grounding rubric.",
    }


def evaluate_human_calibration_sample(sample_path: Path | None = None) -> dict[str, Any]:
    """Evaluate calibrated human ratings against automated judge."""
    path = sample_path or (ROOT / "eval" / "golden" / "human_sample.json")
    if not path.exists():
        raise FileNotFoundError(f"Human sample file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        samples = json.load(f)

    r_ashwin = []
    r_aman = []
    r_judge = []

    results = []
    for s in samples:
        ashwin_score = s.get("rating_ashwin", 4)
        aman_score = s.get("rating_aman", 4)
        case_data = {
            "id": s["id"],
            "question": s["question"],
            "intent": s.get("intent", "forecast"),
            "expect": s.get("expect", {}),
        }
        res = evaluate_quality_rubric(s["answer"], case_data)
        judge_score = res["score"]

        r_ashwin.append(ashwin_score)
        r_aman.append(aman_score)
        r_judge.append(judge_score)

        results.append({
            "id": s["id"],
            "question": s["question"],
            "ashwin": ashwin_score,
            "aman": aman_score,
            "judge": judge_score,
            "rubric_details": res,
        })

    kappa_human = calculate_cohen_kappa(r_ashwin, r_aman)
    kappa_judge_ashwin = calculate_cohen_kappa(r_judge, r_ashwin)
    kappa_judge_aman = calculate_cohen_kappa(r_judge, r_aman)

    return {
        "count": len(samples),
        "cohen_kappa_human_inter_rater": round(kappa_human, 3),
        "cohen_kappa_judge_vs_ashwin": round(kappa_judge_ashwin, 3),
        "cohen_kappa_judge_vs_aman": round(kappa_judge_aman, 3),
        "mean_ashwin_score": round(sum(r_ashwin) / len(r_ashwin), 2),
        "mean_aman_score": round(sum(r_aman) / len(r_aman), 2),
        "mean_judge_score": round(sum(r_judge) / len(r_judge), 2),
        "samples": results,
    }


def main() -> None:
    results = evaluate_human_calibration_sample()
    out_dir = ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "judge_calibration.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Calibration results written to {out_file.relative_to(ROOT)}")
    print(f"Samples evaluated: {results['count']}")
    print(f"Human inter-rater Cohen's kappa (Ashwin vs Aman): {results['cohen_kappa_human_inter_rater']}")
    print(f"Judge vs Ashwin Cohen's kappa: {results['cohen_kappa_judge_vs_ashwin']}")
    print(f"Judge vs Aman Cohen's kappa: {results['cohen_kappa_judge_vs_aman']}")
    print(f"Mean Ashwin score: {results['mean_ashwin_score']}")
    print(f"Mean Aman score: {results['mean_aman_score']}")
    print(f"Mean Judge score: {results['mean_judge_score']}")


if __name__ == "__main__":
    main()
