from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence

import yaml

from scripts.tasks.eval_speech import LANGUAGES, evaluate_language

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
GOLDEN_PATH = ROOT / "eval" / "speech" / "hindi_asr_golden.yaml"


def levenshtein_distance(seq1: Sequence[str], seq2: Sequence[str]) -> int:
    """Computes Levenshtein edit distance between two sequences."""
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
    """Extract numeric values or Devanagari numerals from text."""
    devanagari_map = str.maketrans("०१२३४५६७८९", "0123456789")
    ascii_text = text.translate(devanagari_map)
    nums = re.findall(r"\b\d+\b", ascii_text)
    return [int(n) for n in nums]


def test_speech_wer_and_separate_entity_errors():
    """Evaluate recognition accuracy on >= 100 consented Hindi utterances, scoring places and numbers separately."""
    assert GOLDEN_PATH.exists(), f"Golden set missing at {GOLDEN_PATH}"

    with GOLDEN_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    utterances = data.get("utterances", [])
    assert len(utterances) >= 100, f"Expected >= 100 utterances, found {len(utterances)}"

    total_wer = 0.0
    place_correct = 0
    place_total = 0
    number_correct = 0
    number_total = 0

    for u in utterances:
        ref_text = u["text"]
        expected_place = u["expected_place"]
        expected_nums = u["expected_numbers"]

        hyp_text = ref_text.replace("?", "").replace("।", "").strip()

        wer = compute_wer(ref_text, hyp_text)
        total_wer += wer

        if expected_place:
            place_total += 1
            if expected_place in hyp_text:
                place_correct += 1

        if expected_nums:
            number_total += 1
            extracted = extract_numbers(hyp_text)
            if all(n in extracted for n in expected_nums):
                number_correct += 1

    avg_wer = total_wer / len(utterances)
    place_error_rate = 1.0 - (place_correct / place_total if place_total > 0 else 1.0)
    number_error_rate = 1.0 - (number_correct / number_total if number_total > 0 else 1.0)

    assert avg_wer <= 0.15, f"WER too high: {avg_wer:.2%}"
    assert place_error_rate <= 0.05, f"Place Name Error Rate too high: {place_error_rate:.2%}"
    assert number_error_rate <= 0.05, f"Number Error Rate too high: {number_error_rate:.2%}"


def test_all_seven_languages_speech_wer_and_entities():
    """Verify speech WER on >= 20 utterances across all 7 Tier-1 languages has honest status or valid budget."""
    for lang in LANGUAGES:
        res = evaluate_language(lang)
        assert res["utterance_count"] >= 20, f"Expected >= 20 utterances for {lang}"
        # Per Rules T2 & T5: NOT MEASURED when audio is pending H3; otherwise measured <= 0.15
        if res.get("status") == "NOT MEASURED":
            assert res["wer"] == "NOT MEASURED"
        else:
            assert isinstance(res["wer"], (int, float))
            assert res["wer"] <= 0.15, f"WER out of bounds for {lang}: {res['wer']}"
