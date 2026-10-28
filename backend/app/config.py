from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://trading:trading@localhost:5432/trading"
    redis_url: str = "redis://localhost:6379/0"
    broker_mode: Literal["paper"] = "paper"
    enable_trading: bool = False
    enable_live_trading: bool = False
    risk_per_trade: float = Field(default=0.01, gt=0, le=1)
    max_position_fraction: float = Field(default=0.10, gt=0, le=1)
    max_portfolio_exposure_fraction: float = Field(default=0.80, gt=0, le=1)
    max_open_positions: int = Field(default=10, ge=1)
    max_daily_loss_fraction: float = Field(default=0.02, gt=0, le=1)
    max_drawdown_fraction: float = Field(default=0.15, gt=0, le=1)
    symbol_cooldown_seconds: int = Field(default=3600, ge=0)
    api_auth_enabled: bool = False
    api_key: SecretStr | None = None
    cors_allowed_origins: str = "http://localhost:5173"
    rate_limit_requests: int = Field(default=120, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    @model_validator(mode="after")
    def validate_api_auth(self) -> Self:
        production = self.app_env.lower() in {"production", "prod"}
        if production and not self.api_auth_enabled:
            raise ValueError("API_AUTH_ENABLED must be true in production")
        if self.api_auth_enabled and (
            self.api_key is None or len(self.api_key.get_secret_value()) < 32
        ):
            raise ValueError("API_KEY must contain at least 32 characters when API auth is enabled")
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
