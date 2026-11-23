from fastapi import APIRouter, Request
from trading.deployment.status import DeploymentStatus

from app.api.routes.health import (
    check_broker_adapter,
    check_database,
    check_market_data_provider,
    check_model_service,
    check_redis,
)
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["deployment"])


@router.get("/deployment/status")
async def deployment_status(request: Request) -> dict[str, object]:
    database_ok = await check_database(request.app.state.database_engine)
    redis_ok = await check_redis(request.app.state.redis_client)
    snapshot = DeploymentStatus(get_settings()).snapshot()
    snapshot["status"] = (
        "ok"
        if database_ok
        and redis_ok
        and check_market_data_provider(request)
        and check_broker_adapter(request)
        and check_model_service(request)
        else "degraded"
    )
    snapshot["services"] = {
        "backend": "ready",
        "postgres": "ok" if database_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
        "market_data": "ok" if check_market_data_provider(request) else "unavailable",
        "broker": "ok" if check_broker_adapter(request) else "unavailable",
        "model_service": "ok" if check_model_service(request) else "unavailable",
    }
    return snapshot
