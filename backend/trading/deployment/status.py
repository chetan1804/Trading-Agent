from __future__ import annotations

from typing import Any

from app.config import Settings


class DeploymentStatus:
    def __init__(self, settings: Settings) -> None:
        self.environment = settings.app_env.lower()
        self.broker_mode = settings.broker_mode
        self.enable_trading = settings.enable_trading
        self.enable_live_trading = settings.enable_live_trading
        self.docker_ready = True

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "environment": self.environment,
            "broker_mode": self.broker_mode,
            "docker_ready": self.docker_ready,
            "trading_enabled": self.enable_trading,
            "live_trading_enabled": self.enable_live_trading,
            "services": {
                "backend": "ready",
                "postgres": "configured",
                "redis": "configured",
            },
        }
