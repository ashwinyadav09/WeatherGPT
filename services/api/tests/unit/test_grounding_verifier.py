from __future__ import annotations

import datetime as dt

from services.api.app.conversation.verifier import verify_grounding
from services.api.app.evidence.models import EvidencePacket, PlaceReference, ValueItem


def make_packet(temp: float, rain: float) -> EvidencePacket:
    now = dt.datetime.now(dt.timezone.utc)
    return EvidencePacket(
        id="test_ep_1",
        source="open_meteo.forecast",
        authority_tier=5,
        provenance="documented-sample",
        issued_at=now,
        valid_from=now,
        valid_to=now + dt.timedelta(days=1),
        place=PlaceReference(id="pune", name="Pune", lat=18.52, lon=73.85),
        values=[
            ValueItem(variable="temperature", value=temp, unit="degC"),
            ValueItem(variable="rain", value=rain, unit="mm"),
        ],
        attribution="Weather data by Open-Meteo.com",
        fetched_at=now,
    )


def test_grounding_verifier_valid():
    packet = make_packet(temp=28.5, rain=5.0)
    text = "Tomorrow in Pune expects 5.0 mm rain with temperature around 28.5 degC."
    res = verify_grounding(text, [packet])
    assert bool(res) is True
    assert len(res.reasons) == 0


def test_grounding_verifier_hallucinated_number():
    packet = make_packet(temp=28.5, rain=0.0)
    # 75 mm is hallucinated / ungrounded
    text = "Tomorrow in Pune expects 75.0 mm heavy rain with temperature 28.5 degC."
    res = verify_grounding(text, [packet])
    assert bool(res) is False
    assert any("75" in r for r in res.reasons)


def test_grounding_verifier_forbidden_word():
    packet = make_packet(temp=28.5, rain=0.0)
    text = "It is guaranteed not to rain in Pune tomorrow."
    res = verify_grounding(text, [packet])
    assert bool(res) is False
    assert any("guaranteed" in r.lower() for r in res.reasons)


def test_grounding_verifier_no_evidence_no_numbers():
    text = "Hello, how can I help you with weather updates today?"
    res = verify_grounding(text, [])
    assert bool(res) is True


def test_grounding_verifier_no_evidence_with_numbers():
    text = "It will rain 25 mm."
    res = verify_grounding(text, [])
    assert bool(res) is False


def test_grounding_verifier_adversarial_tampering():
    # Evidence says rain is 5.0 mm and temp is 28.5 degC
    packet = make_packet(temp=28.5, rain=5.0)

    # Adversarial tampering: subtly altered numbers (e.g. 15.0 mm instead of 5.0 mm, 38 degC instead of 28.5 degC)
    adversarial_answer = "According to Open-Meteo, tomorrow in Pune expects 15.0 mm heavy rain and a high of 38.0 degC."
    res = verify_grounding(adversarial_answer, [packet])
    assert bool(res) is False
    assert any("15" in r for r in res.reasons)
    assert any("38" in r for r in res.reasons)
