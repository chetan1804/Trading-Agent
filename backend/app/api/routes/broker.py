from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(prefix="/api", tags=["broker"])


@router.get("/broker/status")
async def broker_status() -> dict[str, object]:
    settings = get_settings()
    mode = "live" if settings.enable_live_trading else "paper"
    return {
        "status": "ok",
        "mode": mode,
        "broker_mode": settings.broker_mode,
        "paper_enabled": not settings.enable_live_trading,
        "live_enabled": settings.enable_live_trading,
        "connected": False,
        "requires_explicit_enable": True,
    }
