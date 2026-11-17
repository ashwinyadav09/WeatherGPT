"""Telegram Bot API channel adapter and alert disseminator (Ticket 13).

Provides zero-cost, grounded weather assistant access and relay-only alert
broadcasts over Telegram without commercial API fees or DLT registration barriers.
Enforces explicit consent on /start and instant unsubscription on /stop.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

from services.api.app.evidence.models import AlertModel
from services.api.app.modules.alerts.engine import point_in_polygon
from services.api.app.modules.forecast.service import ForecastService

logger = logging.getLogger(__name__)


@dataclass
class ChannelResponse:
    reply_text: str
    has_reply: bool = True
    parse_mode: str = "Markdown"


@dataclass
class TelegramUser:
    chat_id: str
    user_name: str | None = None
    consented: bool = False
    language: str = "en"
    lat: float | None = None
    lon: float | None = None
    place_name: str | None = None
    subscribed_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))


class TelegramChannelAdapter:
    """Telegram Bot channel adapter for WeatherGPT."""

    def __init__(self, bot_token: str = "mock_telegram_token") -> None:
        self.bot_token = bot_token
        self.users: dict[str, TelegramUser] = {}
        self.forecast_service = ForecastService()

    def is_user_consented(self, chat_id: str) -> bool:
        user = self.users.get(chat_id)
        return user is not None and user.consented

    async def handle_message(
        self,
        chat_id: str,
        text: str,
        user_name: str | None = None,
    ) -> ChannelResponse:
        clean_text = text.strip()

        # Handle /start with explicit privacy and consent notice
        if clean_text.startswith("/start"):
            user = self.users.get(chat_id)
            if not user:
                user = TelegramUser(chat_id=chat_id, user_name=user_name, consented=True)
                self.users[chat_id] = user
            else:
                user.consented = True

            consent_notice = (
                "🌦️ *Welcome to WeatherGPT (मौसम जीपीटी)!*\n\n"
                "WeatherGPT is a non-commercial, public-interest weather pilot for India.\n\n"
                "*Privacy & Consent Notice:*\n"
                "• We collect only the location you choose to provide to give accurate local forecasts and life-safety alerts.\n"
                "• No data is sold, monetized, or used for advertising.\n"
                "• Official alerts from NDMA SACHET and IMD are relayed as issued without alteration.\n"
                "• You can revoke consent and stop all notifications at any time by sending /stop.\n\n"
                "*How to use:*\n"
                "• Send your location pin (Paperclip 📎 -> Location) to receive alerts for your area.\n"
                "• Ask any weather question, e.g., 'Will it rain tomorrow in Pune?'\n"
                "• Send /help for commands, or /stop to opt out."
            )
            return ChannelResponse(reply_text=consent_notice)

        # Handle /stop (instant opt-out and unsubscription)
        if clean_text in ("/stop", "/optout", "/unsubscribe"):
            if chat_id in self.users:
                self.users[chat_id].consented = False
                self.users[chat_id].lat = None
                self.users[chat_id].lon = None
            return ChannelResponse(
                reply_text="🛑 You have unsubscribed from WeatherGPT and all alert preferences have been removed. "
                "Send /start at any time to reactivate."
            )

        # Handle /help
        if clean_text.startswith("/help"):
            help_text = (
                "ℹ️ *WeatherGPT Telegram Help*\n\n"
                "• Send your GPS location to configure local alerts.\n"
                "• Ask weather questions in English or Hindi (e.g., 'What is the temperature in Delhi today?').\n"
                "• /stop : Opt out and delete alert subscription\n"
                "• /start : Reactivate subscription and view privacy notice"
            )
            return ChannelResponse(reply_text=help_text)

        # Ensure user is consented before processing general queries
        user = self.users.get(chat_id)
        if not user or not user.consented:
            return ChannelResponse(
                reply_text="Please send /start to view and accept the privacy consent notice before using WeatherGPT."
            )

        # Query weather service
        # Extract place if mentioned, or default to user's saved location
        target_lat = user.lat or 18.5204
        target_lon = user.lon or 73.8567
        target_name = user.place_name or "Pune"

        low_query = clean_text.lower()
        if "delhi" in low_query:
            target_lat, target_lon, target_name = 28.6139, 77.2090, "Delhi"
        elif "mumbai" in low_query:
            target_lat, target_lon, target_name = 19.0760, 72.8777, "Mumbai"
        elif "bengaluru" in low_query or "bangalore" in low_query:
            target_lat, target_lon, target_name = 12.9716, 77.5946, "Bengaluru"
        elif "kolkata" in low_query:
            target_lat, target_lon, target_name = 22.5726, 88.3639, "Kolkata"
        elif "pune" in low_query:
            target_lat, target_lon, target_name = 18.5204, 73.8567, "Pune"

        packets = await self.forecast_service.get_forecast(
            place_id=target_name.lower(),
            lat=target_lat,
            lon=target_lon,
            place_name=target_name,
        )

        if not packets:
            return ChannelResponse(reply_text=f"No forecast data currently available for {target_name}.")

        primary_pkt = packets[0]
        temp_val = "N/A"
        precip_val = "0.0 mm"
        for v in primary_pkt.values:
            if v.variable == "temperature_2m" and v.value is not None:
                temp_val = f"{v.value}{v.unit}"
            elif v.variable in ("precipitation", "precipitation_sum") and v.value is not None:
                precip_val = f"{v.value}{v.unit}"

        answer = (
            f"🌤️ *Weather in {target_name}:*\n"
            f"• Temperature: {temp_val}\n"
            f"• Rain / Precipitation: {precip_val}\n\n"
            f"📌 *Evidence & Attribution:*\n"
            f"• Source: `{primary_pkt.source}` (Authority Tier {primary_pkt.authority_tier})\n"
            f"• Issued: {primary_pkt.issued_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"• Attribution: {primary_pkt.attribution}"
        )
        return ChannelResponse(reply_text=answer)

    async def handle_location(
        self,
        chat_id: str,
        latitude: float,
        longitude: float,
    ) -> ChannelResponse:
        user = self.users.get(chat_id)
        if not user:
            user = TelegramUser(chat_id=chat_id, consented=True)
            self.users[chat_id] = user

        user.lat = latitude
        user.lon = longitude

        # Approximate place name resolution
        if abs(latitude - 18.52) < 0.5 and abs(longitude - 73.85) < 0.5:
            user.place_name = "Pune"
        elif abs(latitude - 28.61) < 0.5 and abs(longitude - 77.20) < 0.5:
            user.place_name = "Delhi"
        elif abs(latitude - 19.07) < 0.5 and abs(longitude - 72.87) < 0.5:
            user.place_name = "Mumbai"
        else:
            user.place_name = f"{latitude:.2f}°N, {longitude:.2f}°E"

        return ChannelResponse(
            reply_text=f"📍 Location saved ({user.place_name}). You will receive official relay-only weather alerts for this area."
        )

    async def disseminate_alert(self, alert: AlertModel) -> dict[str, str]:
        """Disseminates relay-only alerts to subscribed users in the impact polygon.

        Never alters text with an LLM (ADR 0001).
        """
        dispatches: dict[str, str] = {}

        # Extract polygon coordinates from alert areas
        polygons: list[list[tuple[float, float]]] = []
        for area in alert.areas:
            poly = area.get("polygon")
            if poly and isinstance(poly, list) and len(poly) >= 3:
                polygons.append(poly)

        area_desc = alert.areas[0].get("area_desc", "Region") if alert.areas else "Region"
        alert_body = alert.text_by_language.get("en", alert.hazard)

        for chat_id, user in self.users.items():
            if not user.consented or user.lat is None or user.lon is None:
                continue

            # Check point-in-polygon matching
            matches = False
            for poly in polygons:
                if point_in_polygon(user.lat, user.lon, poly):
                    matches = True
                    break

            if matches:
                # Format message using official alert text verbatim
                formatted_alert = (
                    f"🚨 *OFFICIAL WEATHER ALERT: {alert.level.upper()} ALERT*\n"
                    f"*Issued by*: {alert.sender} (Official Authority Tier 1)\n"
                    f"*Hazard*: {alert.hazard} ({alert.severity})\n"
                    f"*Area*: {area_desc}\n"
                    f"*Valid*: {alert.sent.strftime('%H:%M')} to {alert.expires.strftime('%H:%M')} UTC\n\n"
                    f"📢 *Details*: {alert_body}\n\n"
                    f"_This is an official public-safety warning relayed as issued._"
                )
                dispatches[chat_id] = formatted_alert

        return dispatches
