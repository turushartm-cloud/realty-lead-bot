"""Configuration with Pydantic Settings validation."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, PostgresDsn, RedisDsn
from typing import List, Optional
import secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid"
    )

    APP_NAME: str = "Realty Lead Bot"
    DEBUG: bool = Field(default=False)
    ENVIRONMENT: str = Field(default="production", pattern="^(development|staging|production)$")

    SECRET_KEY: str = Field(..., min_length=32)
    BOT_TOKEN: str = Field(..., pattern=r"^\d+:[A-Za-z0-9_-]+$")

    API_ID: int = Field(..., gt=0)
    API_HASH: str = Field(..., min_length=10)
    PHONE_NUMBER: str = Field(..., pattern=r"^\+\d{10,15}$")
    # StringSession, сгенерированная локально скриптом scripts/generate_session.py.
    # Файловая сессия на Render не переживёт передеплой (эфемерный диск),
    # а первый логин Telethon требует интерактивный SMS-код, которого на сервере нет.
    TELETHON_SESSION: str = Field(default="")

    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = Field(default=20, ge=5, le=100)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=50)

    REDIS_URL: RedisDsn

    MINI_APP_URL: str = Field(..., pattern=r"^https?://")

    # AI — опционально, есть fallback-провайдеры
    OPENAI_API_KEY: Optional[str] = None
    AI_FILTER_ENABLED: bool = True
    AI_CONFIDENCE_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0)

    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    RATE_LIMIT_PER_MINUTE: int = Field(default=60, ge=10, le=1000)

    MONITORED_GROUPS: List[int] = Field(default_factory=list)
    KEYWORDS: List[str] = Field(default_factory=lambda: [
        "купить квартиру", "продать квартиру", "снять", "сдать",
        "недвижимость", "риелтор", "агент", "ипотека", "жилье",
        "дом", "участок", "коммерческая", "офис", "апартаменты"
    ])

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_strength(cls, v):
        if len(set(v)) < 10:
            raise ValueError("SECRET_KEY must contain at least 10 unique characters")
        return v

    @field_validator("MONITORED_GROUPS", mode="before")
    @classmethod
    def parse_groups(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    @field_validator("KEYWORDS", mode="before")
    @classmethod
    def parse_keywords(cls, v):
        if isinstance(v, str):
            return [x.strip().lower() for x in v.split(",") if x.strip()]
        return v


settings = Settings()
