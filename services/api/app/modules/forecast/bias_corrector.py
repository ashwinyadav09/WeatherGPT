"""Point-forecast bias correction integration service (Ticket 16).

Enforces authority ladder constraints:
  - Corrected outputs remain strictly labeled as model guidance (Authority Tier 4).
  - Official IMD warnings and forecasts (Tier 1 & Tier 2) are NEVER overridden or mutated.
  - Corrected values are applied only when the gate check passes (beats raw model).
"""

from __future__ import annotations

import copy
import datetime as dt

from ml.bias_correction.mos_model import PointForecastMOSModel
from services.api.app.evidence.models import EvidencePacket, ValueItem


def apply_bias_correction_to_forecast(
    packet: EvidencePacket,
    mos_model: PointForecastMOSModel,
    lead_time_hours: int = 24,
) -> EvidencePacket:
    """Applies statistical bias correction (MOS) to a model forecast packet.

    Raises ValueError if called on an official IMD forecast or alert.
    """
    # Strict project rule: official forecasts and warnings must never be overridden or modified
    if packet.authority_tier < 3 or "imd" in packet.source.lower() or "official" in packet.source.lower():
        raise ValueError(
            f"Cannot apply MOS bias correction to official forecast '{packet.source}': "
            "official warnings and forecasts must be relayed as issued without modification."
        )

    # Clone packet to avoid in-place mutation of raw cache
    corrected = copy.deepcopy(packet)

    doy = (
        packet.issued_at.timetuple().tm_yday
        if packet.issued_at
        else dt.datetime.now(dt.timezone.utc).timetuple().tm_yday
    )
    month = packet.issued_at.month if packet.issued_at else dt.datetime.now(dt.timezone.utc).month
    lat = packet.place.lat if packet.place and packet.place.lat is not None else 20.0
    elev = 200.0  # approximate elevation if not provided

    new_values: list[ValueItem] = []
    applied_corrections: list[str] = []

    for item in corrected.values:
        if item.variable in ("temperature_2m", "temperature_2m_max", "temperature_2m_min"):
            if mos_model.should_use_correction(variable="temperature_2m", lead_time_hours=lead_time_hours):
                if isinstance(item.value, (int, float)):
                    corr_temp = mos_model.predict_temperature(
                        raw_temp=float(item.value),
                        day_of_year=doy,
                        elev_m=elev,
                        lat=lat,
                    )
                    new_values.append(
                        ValueItem(
                            variable=item.variable,
                            value=corr_temp,
                            unit=item.unit,
                            step=item.step,
                        )
                    )
                    applied_corrections.append("temperature_2m")
                    continue
        elif item.variable in ("precipitation", "precipitation_sum"):
            if mos_model.should_use_correction(variable="precipitation", lead_time_hours=lead_time_hours):
                if isinstance(item.value, (int, float)):
                    corr_prob = mos_model.predict_rain_probability(
                        raw_rain=float(item.value),
                        month=month,
                        lat=lat,
                    )
                    new_values.append(
                        ValueItem(
                            variable="precipitation_probability",
                            value=round(corr_prob * 100.0, 1),
                            unit="%",
                            step=item.step,
                        )
                    )
                    applied_corrections.append("precipitation_probability")
        new_values.append(item)

    if applied_corrections:
        corrected.values = new_values
        corrected.source = f"{packet.source} (MOS corrected)"
        corrected.authority_tier = 4  # Strictly remains model guidance (Tier 4)
        corrected.attribution = (
            f"{packet.attribution} (MOS bias-corrected against IMD/IEM ground stations; "
            f"model_version={mos_model.MODEL_VERSION}, training_window={mos_model.TRAINING_WINDOW})"
        )

    return corrected
