"""Provider Registry for WeatherGPT (Ticket R1.1).

Central registry and factory for all external service providers and adapters.
Per target architecture (REMEDIATION_PLAN.md, Section 3):
- Builds providers from configuration (FORECAST_PROVIDERS, ALERT_PROVIDERS, TRANSLATION_PROVIDERS, SPEECH_PROVIDERS).
- The ONLY application module that imports concrete adapters.
- Order = priority; the first healthy provider answers; failures fall through and are logged.
- Keeps imd_city registered but excluded unless IMD_ENABLED=true and a key exists.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Callable

from services.api.app.config import Settings
from services.api.app.config import settings as app_settings
from services.api.app.evidence.models import EvidencePacket
from services.api.app.gateways.llm.adapters.base import LLMAdapter
from services.api.app.gateways.llm.adapters.openai_compatible import OpenAICompatibleLLMAdapter
from services.api.app.gateways.llm.adapters.stub import StubLLMAdapter
from services.api.app.gateways.speech.adapters.bhashini import BhashiniSpeechAdapter
from services.api.app.gateways.speech.adapters.sarvam import SarvamSpeechAdapter
from services.api.app.gateways.speech.adapters.stub import StubSpeechAdapter
from services.api.app.gateways.translation.base import TranslationAdapter
from services.api.app.gateways.translation.gateway import TranslationGateway
from services.api.app.gateways.translation.llm_fallback import LLMTranslationAdapter
from services.api.app.gateways.translation.sarvam import SarvamTranslationAdapter
from services.api.app.modules.alerts.sachet_adapter import SachetCAPAdapter
from services.api.app.modules.forecast.adapters.base import ForecastAdapter
from services.api.app.modules.forecast.adapters.ecmwf import ECMWFAdapter
from services.api.app.modules.forecast.adapters.gfs import GFSPointAdapter
from services.api.app.modules.forecast.adapters.imd_city import IMDCityForecastAdapter
from services.api.app.modules.forecast.adapters.open_meteo import OpenMeteoForecastAdapter
from services.api.app.modules.forecast.adapters.stub import StubForecastAdapter
from services.api.app.modules.location.adapters.open_meteo_geocoding import OpenMeteoGeocodingAdapter

logger = logging.getLogger(__name__)


class FailoverForecastProvider(ForecastAdapter):
    """Forecast provider that tries registered providers in priority order.

    If a provider fails or raises an error, it logs the failure and falls through
    to the next provider.
    """

    def __init__(self, providers: list[ForecastAdapter]) -> None:
        self.providers = providers

    @property
    def source_id(self) -> str:
        if self.providers:
            return getattr(self.providers[0], "source_id", "composite.forecast")
        return "none.forecast"

    async def get_forecast(
        self,
        lat: float,
        lon: float,
        place_name: str,
        **kwargs: Any,
    ) -> list[EvidencePacket]:
        if not self.providers:
            raise RuntimeError("No forecast providers configured or available.")

        last_error: Exception | None = None
        for i, provider in enumerate(self.providers):
            p_name = getattr(provider, "source_id", type(provider).__name__)
            try:
                packets = await provider.get_forecast(
                    lat=lat, lon=lon, place_name=place_name, **kwargs
                )
                if packets:
                    return packets
            except Exception as exc:
                last_error = exc
                next_p = (
                    getattr(self.providers[i + 1], "source_id", type(self.providers[i + 1]).__name__)
                    if i + 1 < len(self.providers)
                    else "none"
                )
                logger.warning(
                    "forecast_provider_failed",
                    extra={
                        "provider": p_name,
                        "error": str(exc),
                        "falling_back_to": next_p,
                    },
                )

        logger.error(
            "all_forecast_providers_failed",
            extra={
                "tried": [getattr(p, "source_id", type(p).__name__) for p in self.providers],
                "last_error": str(last_error),
            },
        )
        raise RuntimeError(f"All forecast providers failed: {last_error}")


class ProviderRegistry:
    """Central registry and factory for service adapters."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or app_settings
        self._init_factories()

    def _init_factories(self) -> None:
        self.forecast_factories: dict[str, Callable[[Settings], ForecastAdapter]] = {
            "open_meteo": lambda s: OpenMeteoForecastAdapter(),
            "open-meteo": lambda s: OpenMeteoForecastAdapter(),
            "open_meteo.forecast": lambda s: OpenMeteoForecastAdapter(),
            "imd_city": lambda s: IMDCityForecastAdapter(),
            "imd-city": lambda s: IMDCityForecastAdapter(),
            "imd.city_forecast": lambda s: IMDCityForecastAdapter(),
            "ecmwf": lambda s: ECMWFAdapter(),
            "ecmwf.ifs": lambda s: ECMWFAdapter(),
            "gfs": lambda s: GFSPointAdapter(),
            "gfs.point": lambda s: GFSPointAdapter(),
            "stub": lambda s: StubForecastAdapter(),
            "stub.forecast": lambda s: StubForecastAdapter(),
        }

        self.alert_factories: dict[str, Callable[[Settings], Any]] = {
            "sachet": lambda s: SachetCAPAdapter(),
            "sachet.cap": lambda s: SachetCAPAdapter(),
        }

        self.speech_factories: dict[str, Callable[[Settings], Any]] = {
            "sarvam": lambda s: SarvamSpeechAdapter(
                api_key=s.sarvam_api_key or os.getenv("SARVAM_API_KEY", "")
            ),
            "bhashini": lambda s: BhashiniSpeechAdapter(),
            "stub": lambda s: StubSpeechAdapter(),
        }

        self.geocoding_factories: dict[str, Callable[[Settings], Any]] = {
            "open_meteo": lambda s: OpenMeteoGeocodingAdapter(),
            "open_meteo.geocoding": lambda s: OpenMeteoGeocodingAdapter(),
        }

        self.translation_factories: dict[str, Callable[[Settings], TranslationAdapter]] = {
            "sarvam": lambda s: SarvamTranslationAdapter(
                api_key=s.sarvam_api_key or os.getenv("SARVAM_API_KEY", "")
            ),
            "sarvam.translation": lambda s: SarvamTranslationAdapter(
                api_key=s.sarvam_api_key or os.getenv("SARVAM_API_KEY", "")
            ),
            "llm": lambda s: LLMTranslationAdapter(),
            "llm.translation": lambda s: LLMTranslationAdapter(),
        }

    def _is_forecast_provider_available(self, name: str) -> bool:
        norm = name.lower().replace("-", "_")
        # IMD is excluded unless IMD_ENABLED is true AND IMD_API_KEY exists
        if "imd" in norm:
            has_key = bool(self.settings.imd_api_key or os.getenv("IMD_API_KEY"))
            return self.settings.imd_enabled and has_key
        return True

    def get_available_forecast_providers(self) -> list[ForecastAdapter]:
        """Return instantiated forecast providers in configured priority order."""
        providers: list[ForecastAdapter] = []
        for name in self.settings.forecast_providers:
            norm = name.strip()
            if not self._is_forecast_provider_available(norm):
                logger.info("forecast_provider_excluded", extra={"provider": norm, "reason": "not_enabled_or_no_key"})
                continue

            factory = self.forecast_factories.get(norm)
            if factory:
                providers.append(factory(self.settings))
            else:
                logger.warning("unknown_forecast_provider", extra={"provider": norm})

        if not providers:
            # Fall back to stub if no configured provider is available
            providers.append(StubForecastAdapter())
        return providers

    def get_active_forecast_provider(self) -> ForecastAdapter:
        """Return primary active forecast provider."""
        available = self.get_available_forecast_providers()
        return available[0]

    def get_forecast_provider(self) -> ForecastAdapter:
        """Return FailoverForecastProvider wrapping all available forecast providers."""
        available = self.get_available_forecast_providers()
        return FailoverForecastProvider(available)

    def get_alert_adapter(self, provider_name: str | None = None) -> Any:
        """Return configured alert adapter (default: SachetCAPAdapter)."""
        name = provider_name or (self.settings.alert_providers[0] if self.settings.alert_providers else "sachet")
        factory = self.alert_factories.get(name) or self.alert_factories.get("sachet")
        if factory:
            return factory(self.settings)
        return SachetCAPAdapter()

    def get_speech_adapter(self, provider_name: str | None = None) -> Any:
        """Return configured speech adapter (default: SarvamSpeechAdapter)."""
        name = provider_name or (self.settings.speech_providers[0] if self.settings.speech_providers else "sarvam")
        factory = self.speech_factories.get(name) or self.speech_factories.get("sarvam")
        if factory:
            return factory(self.settings)
        return SarvamSpeechAdapter(api_key=self.settings.sarvam_api_key or os.getenv("SARVAM_API_KEY", ""))

    def get_geocoding_adapter(self, provider_name: str | None = None) -> Any:
        """Return configured geocoding adapter."""
        name = provider_name or "open_meteo"
        factory = self.geocoding_factories.get(name) or self.geocoding_factories.get("open_meteo")
        if factory:
            return factory(self.settings)
        return OpenMeteoGeocodingAdapter()

    def get_llm_gateway(self) -> Any:
        """Return configured LLMGateway with Groq primary, OpenRouter fallback, and Stub fallback."""
        from services.api.app.gateways.llm.gateway import LLMGateway

        groq_key = os.getenv("GROQ_API_KEY", "")
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")

        main_model = self.settings.models.main_model if self.settings.models else "llama-3.3-70b-versatile"
        fallback_model = (
            self.settings.models.fallback.get("main_model", "meta-llama/llama-3.3-70b-instruct")
            if self.settings.models and self.settings.models.fallback
            else "meta-llama/llama-3.3-70b-instruct"
        )

        primary = OpenAICompatibleLLMAdapter(
            base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=groq_key,
            model=main_model,
            provider_name="groq",
        )
        fallback = OpenAICompatibleLLMAdapter(
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=openrouter_key,
            model=fallback_model,
            provider_name="openrouter",
        )
        stub = StubLLMAdapter()
        return LLMGateway(primary=primary, fallback=fallback, stub=stub)

    def get_llm_adapter(self) -> LLMAdapter:
        """Return configured LLM adapter."""
        return self.get_llm_gateway()

    def get_translation_provider(self) -> TranslationGateway:
        """Return configured TranslationGateway with primary and fallback adapters."""
        primary_name = self.settings.translation_providers[0] if self.settings.translation_providers else "sarvam"
        fallback_name = (
            self.settings.translation_providers[1]
            if len(self.settings.translation_providers) > 1
            else "llm"
        )
        primary_factory = self.translation_factories.get(primary_name) or self.translation_factories["sarvam"]
        fallback_factory = self.translation_factories.get(fallback_name) or self.translation_factories["llm"]

        primary = primary_factory(self.settings)
        fallback = fallback_factory(self.settings)
        return TranslationGateway(primary=primary, fallback=fallback)

    def get_orchestrator(
        self,
        forecast_service: Any | None = None,
        location_resolver: Any | None = None,
        llm: Any | None = None,
        translation_gateway: Any | None = None,
        intent_model: Any | None = None,
    ) -> Any:
        """Return configured Orchestrator via the registry."""
        from services.api.app.agent.orchestrator import Orchestrator
        from services.api.app.modules.forecast.service import ForecastService
        from services.api.app.modules.location.resolver import LocationResolver

        if forecast_service is None:
            forecast_service = ForecastService()
            for prov in self.get_available_forecast_providers():
                forecast_service.register_adapter(prov)

        if location_resolver is None:
            location_resolver = LocationResolver(geocoder=self.get_geocoding_adapter())

        return Orchestrator(
            llm=llm or self.get_llm_gateway(),
            forecast_service=forecast_service,
            location_resolver=location_resolver,
            translation_gateway=translation_gateway or self.get_translation_provider(),
            intent_model=intent_model,
        )


# Module-level default registry instance and helper accessors
registry = ProviderRegistry()


def get_forecast_provider(settings: Settings | None = None) -> ForecastAdapter:
    if settings:
        return ProviderRegistry(settings).get_forecast_provider()
    return registry.get_forecast_provider()


def get_active_forecast_provider(settings: Settings | None = None) -> ForecastAdapter:
    if settings:
        return ProviderRegistry(settings).get_active_forecast_provider()
    return registry.get_active_forecast_provider()


def get_alert_adapter(provider_name: str | None = None, settings: Settings | None = None) -> Any:
    if settings:
        return ProviderRegistry(settings).get_alert_adapter(provider_name)
    return registry.get_alert_adapter(provider_name)


def get_speech_adapter(provider_name: str | None = None, settings: Settings | None = None) -> Any:
    if settings:
        return ProviderRegistry(settings).get_speech_adapter(provider_name)
    return registry.get_speech_adapter(provider_name)


def get_geocoding_adapter(settings: Settings | None = None) -> Any:
    if settings:
        return ProviderRegistry(settings).get_geocoding_adapter()
    return registry.get_geocoding_adapter()


def get_llm_adapter(settings: Settings | None = None) -> LLMAdapter:
    if settings:
        return ProviderRegistry(settings).get_llm_adapter()
    return registry.get_llm_adapter()


def get_translation_provider(settings: Settings | None = None) -> TranslationGateway:
    if settings:
        return ProviderRegistry(settings).get_translation_provider()
    return registry.get_translation_provider()


def get_orchestrator(settings: Settings | None = None, **kwargs: Any) -> Any:
    if settings:
        return ProviderRegistry(settings).get_orchestrator(**kwargs)
    return registry.get_orchestrator(**kwargs)

