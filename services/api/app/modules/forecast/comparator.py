from __future__ import annotations

from typing import Any

from services.api.app.evidence.models import EvidencePacket


def detect_forecast_disagreement(
    official: EvidencePacket,
    models: list[EvidencePacket],
    temp_threshold: float = 3.0,
    rain_threshold: float = 5.0,
) -> list[dict[str, Any]]:
    """Compare official forecast with independent model guidance.

    Returns reports of material disagreement (temperature difference > temp_threshold
    or precipitation difference > rain_threshold). Per project rules, material disagreements
    must be presented honestly and labeled distinctly, never silently averaged.
    """
    disagreements = []

    # Map official values by variable name
    official_vals: dict[str, float] = {}
    for item in official.values:
        if isinstance(item.value, (int, float)):
            official_vals[item.variable] = float(item.value)

    for model_pkt in models:
        model_vals: dict[str, float] = {}
        for item in model_pkt.values:
            if isinstance(item.value, (int, float)):
                model_vals[item.variable] = float(item.value)

        conflicting_vars = []

        # Check temperature disagreement
        for var in ["temperature_2m", "temperature_2m_max", "temperature_2m_min"]:
            if var in official_vals and var in model_vals:
                diff = abs(official_vals[var] - model_vals[var])
                if diff >= temp_threshold:
                    conflicting_vars.append(var)

        # Check precipitation disagreement
        for var in ["precipitation", "precipitation_sum"]:
            if var in official_vals and var in model_vals:
                diff = abs(official_vals[var] - model_vals[var])
                if diff >= rain_threshold:
                    conflicting_vars.append(var)

        if conflicting_vars:
            disagreements.append({
                "has_material_disagreement": True,
                "variables": conflicting_vars,
                "official_source": official.source,
                "model_source": model_pkt.source,
                "official_values": {v: official_vals[v] for v in conflicting_vars if v in official_vals},
                "model_values": {v: model_vals[v] for v in conflicting_vars if v in model_vals},
                "note": f"Material disagreement between {official.source} and {model_pkt.source} on {', '.join(conflicting_vars)}.",
            })

    return disagreements
