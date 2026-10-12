from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.routes.health import router as health_router
from app.api.routes.portfolio import router as portfolio_router
from app.config import Settings, get_settings
from app.core.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        application.state.database_engine = create_async_engine(app_settings.database_url)
        application.state.redis_client = Redis.from_url(
            app_settings.redis_url, decode_responses=True
        )
        try:
            yield
        finally:
            await application.state.redis_client.aclose()
            await application.state.database_engine.dispose()

    application = FastAPI(
        title="AI Automated Trading Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(portfolio_router)
    return application


app = create_app()
