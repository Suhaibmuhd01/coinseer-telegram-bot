from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Application Settings
    APP_NAME: str = "CoinSeer"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # Telegram Bot Configuration
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot Token from @BotFather")
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(default=None, description="Public HTTPS endpoint for Telegram webhooks")
    TELEGRAM_WEBHOOK_SECRET: Optional[str] = Field(default="secret_token_coinseer_enterprise", description="Secret token for Telegram webhook validation")
    TELEGRAM_WEBAPP_URL: Optional[str] = Field(default=None, description="Public HTTPS endpoint for the Telegram WebApp Mini-App")

    # Database Settings (PostgreSQL AsyncPG)
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://coinseer_user:coinseer_secret_pass@localhost:5432/coinseer_db",
        description="Async PostgreSQL connection URL"
    )
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECS: int = 1800

    # Redis Settings
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Async Redis connection URL"
    )
    CACHE_DEFAULT_TTL_SECS: int = 60

    # External APIs
    COINGECKO_API_KEY: Optional[str] = None
    COINGECKO_IS_PRO: bool = False
    COINMARKETCAP_API_KEY: Optional[str] = None
    CRYPTOPANIC_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # APM & Sentry
    SENTRY_DSN: Optional[str] = None

    # Supported Currencies & Defaults
    SUPPORTED_FIAT: List[str] = ["usd", "eur", "gbp", "jpy", "aud", "cad", "chf", "cny"]
    DEFAULT_FIAT: str = "usd"

    # Whale Alert Threshold
    WHALE_ALERT_THRESHOLD_USD: float = 1_000_000.0

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Optional[str]) -> str:
        if not v:
            return "postgresql+asyncpg://coinseer_user:coinseer_secret_pass@localhost:5432/coinseer_db"
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()
