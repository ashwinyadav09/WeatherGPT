"""Fixture loader for tests and evaluations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
INDEX_PATH = ROOT / "eval" / "fixtures" / "index.json"

PROVENANCE_VALUES = ("live-recorded", "documented-sample", "spec-only", "synthetic")


def load_fixture_index() -> list[dict[str, Any]]:
    """Load the full fixture index."""
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Fixture index not found at {INDEX_PATH}")
    with INDEX_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def list_fixtures(source: str | None = None) -> list[dict[str, Any]]:
    """List fixtures matching an optional source."""
    index = load_fixture_index()
    if source is None:
        return index
    return [item for item in index if item.get("source") == source]


def get_fixture(file_or_rel_path: str) -> Any:
    """Load a fixture file and parse as JSON (or return raw text if not JSON)."""
    clean_path = file_or_rel_path.replace("\\", "/").lstrip("/")
    target = ROOT / clean_path
    if not target.exists():
        raise FileNotFoundError(f"Fixture file does not exist: {target}")

    text = target.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except Exception:
        return text


def validate_fixture_provenance(data: dict[str, Any]) -> str:
    """Validate that fixture metadata contains a valid provenance label."""
    provenance = data.get("_provenance")
    if not provenance or provenance not in PROVENANCE_VALUES:
        raise ValueError(f"Invalid or missing _provenance in fixture: {provenance}")
    return str(provenance)
