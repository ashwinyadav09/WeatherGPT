from __future__ import annotations

import re

from services.api.app.evidence.models import EvidencePacket


class VerificationResult:
    def __init__(self, is_grounded: bool, reasons: list[str]) -> None:
        self.is_grounded = is_grounded
        self.reasons = reasons

    def __bool__(self) -> bool:
        return self.is_grounded


FORBIDDEN_WORDS = [
    "guaranteed",
    "definitely will not rain",
    "you should evacuate",
    "you must evacuate",
]


def extract_numbers_from_text(text: str) -> list[float]:
    # Extract floating point and integer numbers from text
    # Avoid picking up ISO year stamps like 2026 or dates
    cleaned = re.sub(r"\b20\d\d\b", "", text)
    tokens = re.findall(r"[-+]?\d*\.?\d+", cleaned)
    nums = []
    for t in tokens:
        try:
            if t not in (".", "-", "+", ""):
                nums.append(float(t))
        except ValueError:
            continue
    return nums


def extract_numbers_from_evidence(packets: list[EvidencePacket]) -> set[float]:
    allowed: set[float] = set()
    for p in packets:
        for val_item in p.values:
            if isinstance(val_item.value, (int, float)):
                f = float(val_item.value)
                allowed.add(f)
                allowed.add(round(f))
                allowed.add(float(int(f)))
            elif isinstance(val_item.value, str):
                try:
                    f = float(val_item.value)
                    allowed.add(f)
                    allowed.add(round(f))
                except ValueError:
                    pass
    return allowed


def verify_grounding(answer_text: str, evidence_packets: list[EvidencePacket]) -> VerificationResult:
    reasons = []

    # Check forbidden words
    lower_text = answer_text.lower()
    for word in FORBIDDEN_WORDS:
        if word in lower_text:
            reasons.append(f"Forbidden phrase found: '{word}'")

    if not evidence_packets:
        # If no evidence packet provided and text has numerical statements
        nums = extract_numbers_from_text(answer_text)
        if nums:
            reasons.append(f"Numbers present without evidence: {nums}")
            return VerificationResult(False, reasons)
        return VerificationResult(len(reasons) == 0, reasons)

    allowed_nums = extract_numbers_from_evidence(evidence_packets)
    answer_nums = extract_numbers_from_text(answer_text)

    for num in answer_nums:
        # Check if num is close to any allowed number
        matched = False
        for allowed in allowed_nums:
            if abs(num - allowed) < 0.05 or abs(num - round(allowed)) < 0.05:
                matched = True
                break
        if not matched:
            reasons.append(f"Ungrounded number {num} in answer")

    return VerificationResult(len(reasons) == 0, reasons)
