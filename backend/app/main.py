from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from trading.broker.paper_broker import PaperBroker
from trading.risk.manager import RiskManager

from app.api.routes.agents import router as agents_router
from app.api.routes.ai import router as ai_router
from app.api.routes.backtests import router as backtests_router
from app.api.routes.broker import router as broker_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.deployment import router as deployment_router
from app.api.routes.features import router as features_router
from app.api.routes.health import router as health_router
from app.api.routes.market_data import router as market_data_router
from app.api.routes.ml import router as ml_router
from app.api.routes.monitoring import router as monitoring_router
from app.api.routes.paper_trading import router as paper_trading_router
from app.api.routes.performance import router as performance_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.risk import router as risk_router
from app.api.routes.strategies import router as strategies_router
from app.config import Settings, get_settings
from app.core.logging import configure_logging
from app.repositories.market_data import MarketDataRepository
from app.repositories.paper_orders import PaperOrderRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_async_engine(app_settings.database_url)
        application.state.database_engine = engine
        application.state.database_session_factory = async_sessionmaker(
            engine,
            expire_on_commit=False,
        )
        application.state.redis_client = Redis.from_url(
            app_settings.redis_url, decode_responses=True
        )
        application.state.risk_manager = RiskManager(enabled=app_settings.enable_trading)
        application.state.paper_broker = PaperBroker(
            initial_cash=100_000.0,
            risk_manager=application.state.risk_manager,
        )
        try:
            if app_settings.app_env == "test":
                persisted_bars = {}
                persisted_orders = []
            else:
                async with application.state.database_session_factory() as session:
                    market_repository = MarketDataRepository(session)
                    order_repository = PaperOrderRepository(session)
                    persisted_bars = await market_repository.list_all()
                    persisted_orders = await order_repository.list_all()
            application.state.market_data_store = persisted_bars
            application.state.paper_broker.restore_orders(persisted_orders)
            yield
        finally:
            await application.state.redis_client.aclose()
            await application.state.database_engine.dispose()

    application = FastAPI(
        title="AI Automated Trading Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.risk_manager = RiskManager(enabled=app_settings.enable_trading)
    application.state.paper_broker = PaperBroker(
        initial_cash=100_000.0,
        risk_manager=application.state.risk_manager,
    )
    application.state.market_data_store: dict[str, list[dict[str, object]]] = {}
    application.include_router(health_router)
    application.include_router(market_data_router)
    application.include_router(features_router)
    application.include_router(strategies_router)
    application.include_router(backtests_router)
    application.include_router(risk_router)
    application.include_router(paper_trading_router)
    application.include_router(portfolio_router)
    application.include_router(dashboard_router)
    application.include_router(ai_router)
    application.include_router(agents_router)
    application.include_router(monitoring_router)
    application.include_router(deployment_router)
    application.include_router(broker_router)
    application.include_router(performance_router)
    application.include_router(ml_router)
    return application


app = create_app()
