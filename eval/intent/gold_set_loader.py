"""Loader and validator for the Human Gold Test Set H1 (Ticket R12 / Table 2 H1).

Enforces Rule T1/T2/T6:
- The agent does not generate the gold test set.
- 350 human-written and verified queries (50 per Tier-1 language: en, hi, bn, mr, te, ta, or).
- When fewer than 350 queries are present, returns empty/partial and signals NOT MEASURED.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
GOLD_DIR = ROOT / "eval" / "intent"
GOLD_SET_PATH = GOLD_DIR / "gold_test_set.json"

TIER1_LANGUAGES = ["en", "hi", "bn", "mr", "te", "ta", "or"]
VALID_INTENTS = {
    "current_conditions",
    "forecast",
    "alert",
    "advisory",
    "climate_history",
    "general_knowledge",
    "out_of_domain",
}
REQUIRED_QUERIES_PER_LANG = 50
TOTAL_REQUIRED_QUERIES = 350


class GoldSetValidationError(Exception):
    """Raised when the human gold set fails validation."""


def load_gold_test_set(path: Path | None = None) -> list[dict[str, Any]]:
    """Load and validate the human gold test set H1.

    Returns the list of 350 query dictionaries if valid and complete.
    Returns empty list if the file is missing or contains fewer than 350 valid queries.
    """
    file_path = path or GOLD_SET_PATH
    if not file_path.exists():
        return []

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    # Count by language
    by_lang: dict[str, list[dict[str, Any]]] = {lang: [] for lang in TIER1_LANGUAGES}
    valid_queries: list[dict[str, Any]] = []

    for item in data:
        if not isinstance(item, dict):
            continue
        q = item.get("query", "").strip()
        lang = item.get("language", "").strip()
        intent = item.get("intent", "").strip()
        verified_by = item.get("verified_by", "").strip()

        if not q or not lang or intent not in VALID_INTENTS:
            continue
        if not verified_by or verified_by.startswith("unverified") or verified_by == "human_contributor_id":
            # Unverified or placeholder query
            continue

        if lang in by_lang:
            by_lang[lang].append(item)
            valid_queries.append(item)

    # Check completeness
    if len(valid_queries) < TOTAL_REQUIRED_QUERIES:
        return []

    for lang in TIER1_LANGUAGES:
        if len(by_lang[lang]) < REQUIRED_QUERIES_PER_LANG:
            return []

    return valid_queries


def is_gold_set_ready(path: Path | None = None) -> bool:
    """Check if the gold set H1 has arrived and satisfies all 350 human verified queries."""
    queries = load_gold_test_set(path)
    return len(queries) >= TOTAL_REQUIRED_QUERIES
