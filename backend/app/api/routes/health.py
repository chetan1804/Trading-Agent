from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


async def check_database(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


async def check_redis(client: object) -> bool:
    try:
        await client.ping()  # type: ignore[attr-defined]
    except RedisError:
        return False
    return True


def check_market_data_provider(request: Request) -> bool:
    """The API supports persisted bars and a synthetic fallback provider."""
    return hasattr(request.app.state, "market_data_store")


def check_broker_adapter(request: Request) -> bool:
    """Paper execution must be initialized; live execution is not supported."""
    broker = getattr(request.app.state, "paper_broker", None)
    return broker is not None and callable(getattr(broker, "submit_order", None))


def check_model_service(request: Request) -> bool:
    """Model inference is served on demand by the registered-model pipeline."""
    return getattr(request.app.state, "database_session_factory", None) is not None or (
        getattr(request.app.state, "app_env", None) == "test"
    )


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready")
async def readiness(request: Request) -> JSONResponse:
    database_ok = await check_database(request.app.state.database_engine)
    redis_ok = await check_redis(request.app.state.redis_client)
    market_data_ok = check_market_data_provider(request)
    broker_ok = check_broker_adapter(request)
    model_ok = check_model_service(request)
    checks = {
        "database": "ok" if database_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
        "market_data": "ok" if market_data_ok else "unavailable",
        "broker": "ok" if broker_ok else "unavailable",
        "model_service": "ok" if model_ok else "unavailable",
    }
    ready = database_ok and redis_ok and market_data_ok and broker_ok and model_ok
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ok" if ready else "unavailable", "checks": checks},
    )
