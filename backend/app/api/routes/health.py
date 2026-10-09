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


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready")
async def readiness(request: Request) -> JSONResponse:
    database_ok = await check_database(request.app.state.database_engine)
    redis_ok = await check_redis(request.app.state.redis_client)
    checks = {
        "database": "ok" if database_ok else "unavailable",
        "redis": "ok" if redis_ok else "unavailable",
    }
    ready = database_ok and redis_ok
    return JSONResponse(
        status_code=status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ok" if ready else "unavailable", "checks": checks},
    )
