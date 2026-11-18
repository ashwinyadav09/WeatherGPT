"""Seam tests for Telegram Extra Channel Adapter & Disseminator (Ticket 13)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from services.api.app.evidence.models import AlertModel
from services.api.app.modules.channels.telegram import TelegramChannelAdapter


@pytest.fixture
def telegram_adapter() -> TelegramChannelAdapter:
    return TelegramChannelAdapter(bot_token="test_mock_token")


def test_channel_cost_check_report():
    root = Path(__file__).resolve().parents[4]
    doc_path = root / "docs" / "channel-cost-check.md"
    if not doc_path.exists():
        doc_path = root / "Docs" / "channel-cost-check.md"
    assert doc_path.exists(), "docs/channel-cost-check.md must exist"

    text = doc_path.read_text(encoding="utf-8")
    assert "Telegram" in text
    assert "WhatsApp" in text
    assert "SMS" in text
    assert "IVR" in text
    assert "₹0.00" in text or "free" in text.lower()


@pytest.mark.asyncio
async def test_telegram_channel_consent_and_opt_out(telegram_adapter: TelegramChannelAdapter):
    chat_id = "user_12345"

    # 1. User sends /start
    res_start = await telegram_adapter.handle_message(
        chat_id=chat_id,
        text="/start",
        user_name="Aman",
    )
    assert res_start.has_reply is True
    assert "WeatherGPT" in res_start.reply_text
    assert (
        "consent" in res_start.reply_text.lower()
        or "अनुमति" in res_start.reply_text
        or "privacy" in res_start.reply_text.lower()
    )
    assert telegram_adapter.is_user_consented(chat_id) is True

    # 2. User sends /stop (opt out)
    res_stop = await telegram_adapter.handle_message(
        chat_id=chat_id,
        text="/stop",
        user_name="Aman",
    )
    assert res_stop.has_reply is True
    assert "unsubscribed" in res_stop.reply_text.lower() or "stopped" in res_stop.reply_text.lower()
    assert telegram_adapter.is_user_consented(chat_id) is False


@pytest.mark.asyncio
async def test_telegram_channel_question_and_grounded_answer(telegram_adapter: TelegramChannelAdapter):
    chat_id = "user_67890"
    # Ensure user is consented
    await telegram_adapter.handle_message(chat_id=chat_id, text="/start")

    # Send location update
    loc_res = await telegram_adapter.handle_location(
        chat_id=chat_id,
        latitude=18.5204,
        longitude=73.8567,
    )
    assert "location saved" in loc_res.reply_text.lower() or "pune" in loc_res.reply_text.lower()

    # Ask weather question
    query_res = await telegram_adapter.handle_message(
        chat_id=chat_id,
        text="Will it rain tomorrow in Pune?",
    )
    assert query_res.has_reply is True
    assert len(query_res.reply_text) > 0
    # Must include evidence source or attribution
    assert (
        "Source:" in query_res.reply_text
        or "attribution" in query_res.reply_text.lower()
        or "Open-Meteo" in query_res.reply_text
        or "IMD" in query_res.reply_text
    )


@pytest.mark.asyncio
async def test_telegram_channel_alert_dissemination(telegram_adapter: TelegramChannelAdapter):
    chat_subscribed = "user_pune_alert"
    chat_unsubscribed = "user_opted_out"

    # User 1: Pune, consented
    await telegram_adapter.handle_message(chat_id=chat_subscribed, text="/start")
    await telegram_adapter.handle_location(chat_id=chat_subscribed, latitude=18.5204, longitude=73.8567)

    # User 2: Pune, then opted out
    await telegram_adapter.handle_message(chat_id=chat_unsubscribed, text="/start")
    await telegram_adapter.handle_location(chat_id=chat_unsubscribed, latitude=18.5204, longitude=73.8567)
    await telegram_adapter.handle_message(chat_id=chat_unsubscribed, text="/stop")

    # Construct official alert
    now = dt.datetime.now(dt.timezone.utc)
    alert = AlertModel(
        id="sachet:alert-pune-001",
        sender="NDMA SACHET",
        sent=now,
        status="Actual",
        msg_type="Alert",
        hazard="Heavy Rain",
        severity="Severe",
        urgency="Expected",
        certainty="Likely",
        onset=now,
        expires=now + dt.timedelta(hours=6),
        areas=[
            {
                "area_desc": "Pune, Maharashtra",
                "polygon": [(18.4, 73.7), (18.6, 73.7), (18.6, 73.9), (18.4, 73.9)],
            }
        ],
        text_by_language={
            "en": (
                "Orange Alert: Heavy to Very Heavy Rain expected in Pune. Stay indoors and avoid waterlogged areas. "
                "Avoid traveling through low-lying flooded roads."
            )
        },
        source_url="https://sachet.ndma.gov.in",
        level="orange",
    )

    dispatches = await telegram_adapter.disseminate_alert(alert)

    # Subscribed Pune user should receive the alert
    assert chat_subscribed in dispatches
    msg = dispatches[chat_subscribed]
    assert "NDMA SACHET" in msg
    assert "Heavy to Very Heavy Rain" in msg or "Heavy Rain" in msg
    assert "Avoid traveling" in msg or "Stay indoors" in msg

    # Opted-out user must NEVER receive push alerts
    assert chat_unsubscribed not in dispatches
