#!/usr/bin/env python3
"""Speech ASR Evaluation for WeatherGPT (Ticket R8.2 / R18.4).

Evaluates Word Error Rate (WER), Place Name Error Rate (PNER), and Number Error Rate (NER)
across all 7 Tier-1 languages:
- English (en), Hindi (hi), Bengali (bn), Marathi (mr), Telugu (te), Tamil (ta), Odia (or)

Adheres strictly to Section 2 (truthfulness rules):
- T1 & T5: Zero simulation, no artificial dropout of words, no minimum budget constraints.
- If real recorded audio is not available, status is reported as NOT MEASURED.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEECH_DIR = ROOT / "eval" / "speech"
REPORTS_DIR = ROOT / "reports"
RESULTS_DIR = ROOT / "eval" / "results"

LANGUAGES = ["en", "hi", "bn", "mr", "te", "ta", "or"]

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
TELUGU_DIGITS = str.maketrans("౦౧౨౩౪౫౬౭౮౯", "0123456789")
TAMIL_DIGITS = str.maketrans("௦౧౨౩౪౫౬౭౮౯", "0123456789")
ODIA_DIGITS = str.maketrans("୦୧୨୩୪୫୬୭୮୯", "0123456789")


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


def levenshtein_distance(seq1: Sequence[str], seq2: Sequence[str]) -> int:
    size_x = len(seq1) + 1
    size_y = len(seq2) + 1
    matrix = [[0] * size_y for _ in range(size_x)]
    for x in range(size_x):
        matrix[x][0] = x
    for y in range(size_y):
        matrix[0][y] = y

    for x in range(1, size_x):
        for y in range(1, size_y):
            if seq1[x - 1] == seq2[y - 1]:
                matrix[x][y] = matrix[x - 1][y - 1]
            else:
                matrix[x][y] = min(
                    matrix[x - 1][y] + 1,  # deletion
                    matrix[x][y - 1] + 1,  # insertion
                    matrix[x - 1][y - 1] + 1,  # substitution
                )
    return matrix[size_x - 1][size_y - 1]


def compute_wer(ref: str, hyp: str) -> float:
    ref_words = ref.strip().split()
    hyp_words = hyp.strip().split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    dist = levenshtein_distance(ref_words, hyp_words)
    return dist / len(ref_words)


def extract_numbers(text: str) -> list[int]:
    translated = (
        text.translate(DEVANAGARI_DIGITS)
        .translate(BENGALI_DIGITS)
        .translate(TELUGU_DIGITS)
        .translate(TAMIL_DIGITS)
        .translate(ODIA_DIGITS)
    )
    nums = re.findall(r"\d+", translated)
    return [int(n) for n in nums]


def match_place(expected_place: str, expected_place_en: str, hyp_text: str) -> bool:
    """Check if expected place matches in hypothesis text, accounting for Indic locative suffixes."""
    if not expected_place and not expected_place_en:
        return True
    if expected_place and expected_place in hyp_text:
        return True
    if expected_place_en and expected_place_en.lower() in hyp_text.lower():
        return True
    if expected_place:
        stem1 = expected_place[:-1] if len(expected_place) > 3 else expected_place
        if stem1 in hyp_text:
            return True
        stem2 = expected_place[:-2] if len(expected_place) > 4 else stem1
        if stem2 in hyp_text:
            return True
    return False


def evaluate_language(lang: str) -> dict[str, Any]:
    file_candidates = [SPEECH_DIR / f"{lang}_asr_golden.yaml"]
    if lang == "hi":
        file_candidates.append(SPEECH_DIR / "hindi_asr_golden.yaml")

    golden_file = None
    for cand in file_candidates:
        if cand.exists():
            golden_file = cand
            break

    if not golden_file:
        return {
            "language": lang,
            "status": "NOT MEASURED",
            "reason": "Missing golden yaml file",
            "utterance_count": 0,
            "wer": "NOT MEASURED",
            "pner": "NOT MEASURED",
            "ner": "NOT MEASURED",
        }

    with golden_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    utterances = data.get("utterances", [])

    # Per R8.2 and R18.4: No simulation. Real audio evaluation requires audio files.
    # When real audio is not yet wired to live ASR, we report NOT MEASURED honestly.
    return {
        "language": lang,
        "utterance_count": len(utterances),
        "status": "NOT MEASURED",
        "reason": "Real audio files pending human task H3",
        "wer": "NOT MEASURED",
        "pner": "NOT MEASURED",
        "ner": "NOT MEASURED",
    }


def main() -> int:
    print("\nRunning Speech ASR Evaluation across 7 Tier-1 Languages (Rule T1: Real ML only)...")
    languages_report: dict[str, Any] = {}
    total_utterances = 0

    for lang in LANGUAGES:
        res = evaluate_language(lang)
        languages_report[lang] = res
        total_utterances += res.get("utterance_count", 0)
        print(f"  [{lang.upper()}] Utterances: {res.get('utterance_count', 0)} | Status: {res.get('status')}")

    report = {
        "schema_version": "2",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "git_sha": git_sha(),
        "provenance": "recorded_reference_transcripts_pending_audio",
        "total_languages": len(LANGUAGES),
        "total_utterances": total_utterances,
        "overall_status": "NOT MEASURED",
        "notes": "Simulated ASR hypothesis generation deleted per Ticket R8.2. Real audio evaluation scheduled in R18.4.",
        "languages": languages_report,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for out_path in [REPORTS_DIR / "speech_wer_report.json", RESULTS_DIR / "speech_wer_report.json"]:
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Wrote {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
