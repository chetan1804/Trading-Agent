from functools import lru_cache
from typing import Literal

from pydantic import Field
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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
