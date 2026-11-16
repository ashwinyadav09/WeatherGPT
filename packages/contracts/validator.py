from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas"

_CACHE: dict[str, dict[str, Any]] = {}


def get_schema(name: str) -> dict[str, Any]:
    if name not in _CACHE:
        path = SCHEMAS_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Schema {name}.json not found at {path}")
        with path.open("r", encoding="utf-8") as f:
            _CACHE[name] = json.load(f)
    return _CACHE[name]


def validate_schema(name: str, instance: dict[str, Any]) -> None:
    schema = get_schema(name)
    jsonschema.validate(instance=instance, schema=schema)
