"""Architecture tests for WeatherGPT (Ticket R1.1).

Enforces:
1. No module in services/api/app/ outside of */adapters/* and registry.py may import concrete provider adapters.
2. Concrete adapters must only be accessed and instantiated via services.api.app.registry.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
APP_DIR = ROOT / "services" / "api" / "app"

# Concrete provider adapter class names that must not be imported outside adapters/ and registry.py
CONCRETE_PROVIDER_CLASSES = {
    "OpenMeteoForecastAdapter",
    "IMDCityForecastAdapter",
    "ECMWFAdapter",
    "GFSPointAdapter",
    "StubForecastAdapter",
    "SarvamSpeechAdapter",
    "BhashiniSpeechAdapter",
    "StubSpeechAdapter",
    "OpenMeteoGeocodingAdapter",
    "OpenAICompatibleLLMAdapter",
    "StubLLMAdapter",
    "SachetCAPAdapter",
}


def test_no_concrete_provider_imports_outside_adapters_and_registry():
    """Verify that nothing in services/api/app/ outside adapters/ and registry.py imports concrete providers."""
    violations: list[str] = []

    assert APP_DIR.exists(), f"App directory {APP_DIR} does not exist"

    for py_file in APP_DIR.rglob("*.py"):
        rel_path = py_file.relative_to(APP_DIR).as_posix()

        # Allowed paths: files inside any "adapters" directory, or registry.py
        if "/adapters/" in f"/{rel_path}/" or rel_path == "registry.py":
            continue

        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(py_file))
        except SyntaxError as e:
            violations.append(f"{rel_path}: SyntaxError {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # e.g. import services.api.app.modules.forecast.adapters.open_meteo
                    if ".adapters." in alias.name:
                        violations.append(
                            f"{rel_path}:{node.lineno} imports adapter module '{alias.name}'"
                        )
                    if alias.name in CONCRETE_PROVIDER_CLASSES:
                        violations.append(
                            f"{rel_path}:{node.lineno} imports concrete provider '{alias.name}'"
                        )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                # Check if importing from an adapters package/module
                # Allowed: importing from base interface module (e.g. .base) if type annotating,
                # but NOT concrete adapter files like .open_meteo, .sarvam, etc.
                if ".adapters." in mod or mod.endswith(".adapters"):
                    for alias in node.names:
                        if alias.name in CONCRETE_PROVIDER_CLASSES or (
                            not mod.endswith(".base") and alias.name != "base"
                        ):
                            violations.append(
                                f"{rel_path}:{node.lineno} imports '{alias.name}' from '{mod}'"
                            )
                for alias in node.names:
                    if alias.name in CONCRETE_PROVIDER_CLASSES:
                        violations.append(
                            f"{rel_path}:{node.lineno} imports concrete provider '{alias.name}'"
                        )

    assert not violations, (
        "Architectural violation: concrete provider adapters imported outside adapters/ and registry.py:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
