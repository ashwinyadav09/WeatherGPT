from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = ROOT / "config"


class SourceConfig(BaseModel):
    id: str
    name: str
    base_url: str
    authority_tier: int
    ttl_seconds: int
    rate_limit: str
    attribution: str
    licence_note: str
    enabled: bool = True


class ModelRoleConfig(BaseModel):
    provider: str
    base_url_env: str
    api_key_env: str
    main_model: str
    fast_model: str
    selection_notes: str = ""
    fallback: dict[str, Any] | None = None


class LanguageConfig(BaseModel):
    code: str
    native_name: str
    english_name: str
    tier: int
    asr_provider: str
    tts_provider: str
    enabled: bool = True


class Settings(BaseModel):
    env: str = Field(default_factory=lambda: os.getenv("ENV", "dev"))
    tz: str = Field(default_factory=lambda: os.getenv("TZ", "UTC"))
    public_base_url: str = Field(default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "http://localhost:5173"))
    allowed_origins: list[str] = Field(
        default_factory=lambda: [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    )
    admin_token: str = Field(default_factory=lambda: os.getenv("ADMIN_TOKEN", "dev-secret-token"))
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql+asyncpg://weathergpt:change-me@localhost:5432/weathergpt")
    )
    redis_url: str = Field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    imd_enabled: bool = Field(default_factory=lambda: os.getenv("IMD_ENABLED", "false").lower() in ("true", "1", "yes"))
    agromet_fixture_enabled: bool = Field(default_factory=lambda: os.getenv("AGROMET_FIXTURE_ENABLED", "false").lower() in ("true", "1", "yes"))
    forecast_primary: str = Field(default_factory=lambda: os.getenv("FORECAST_PRIMARY", "open-meteo"))
    forecast_providers: list[str] = Field(
        default_factory=lambda: [p.strip() for p in os.getenv("FORECAST_PROVIDERS", "open_meteo").split(",") if p.strip()]
    )
    alert_providers: list[str] = Field(
        default_factory=lambda: [p.strip() for p in os.getenv("ALERT_PROVIDERS", "sachet").split(",") if p.strip()]
    )
    translation_providers: list[str] = Field(
        default_factory=lambda: [p.strip() for p in os.getenv("TRANSLATION_PROVIDERS", "sarvam,llm").split(",") if p.strip()]
    )
    speech_providers: list[str] = Field(
        default_factory=lambda: [p.strip() for p in os.getenv("SPEECH_PROVIDERS", "sarvam").split(",") if p.strip()]
    )
    voice_enabled: bool = Field(
        default_factory=lambda: os.getenv("VOICE_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    sarvam_api_key: str = Field(default_factory=lambda: os.getenv("SARVAM_API_KEY", ""))
    imd_api_key: str = Field(default_factory=lambda: os.getenv("IMD_API_KEY", ""))

    @field_validator(
        "forecast_providers", "alert_providers", "translation_providers", "speech_providers", mode="before"
    )
    @classmethod
    def _parse_comma_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, (list, tuple)):
            return [str(item).strip() for item in v if str(item).strip()]
        return []

    sources: list[SourceConfig] = Field(default_factory=list)
    models: ModelRoleConfig | None = None
    languages: list[LanguageConfig] = Field(default_factory=list)


def load_settings() -> Settings:
    settings = Settings()

    sources_file = CONFIG_DIR / "sources.yaml"
    if sources_file.exists():
        with sources_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            raw_sources = data.get("sources", [])
            sources = []
            for s in raw_sources:
                if "imd" in s.get("id", ""):
                    s["enabled"] = settings.imd_enabled
                sources.append(SourceConfig(**s))
            settings.sources = sources

    models_file = CONFIG_DIR / "models.yaml"
    if models_file.exists():
        with models_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if "models" in data:
                settings.models = ModelRoleConfig(**data["models"])

    languages_file = CONFIG_DIR / "languages.yaml"
    if languages_file.exists():
        with languages_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            raw_langs = data.get("languages", [])
            settings.languages = [LanguageConfig(**lang) for lang in raw_langs]

    return settings


settings = load_settings()
