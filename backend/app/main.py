import asyncio
import hashlib
import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from trading.broker.paper_broker import PaperBroker
from trading.risk.limits import RiskLimits
from trading.risk.manager import RiskManager

from app.api.routes.agents import router as agents_router
from app.api.routes.ai import router as ai_router
from app.api.routes.audit import router as audit_router
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
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.market_data import MarketDataRepository
from app.repositories.paper_orders import PaperOrderRepository
from app.repositories.paper_portfolio import PaperPortfolioRepository

logger = logging.getLogger(__name__)

_RATE_LIMIT_SCRIPT = """
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_count = 0
local retry_after = window
for _, key in ipairs(KEYS) do
    local count = redis.call('INCR', key)
    if count == 1 then
        redis.call('EXPIRE', key, window)
    end
    local ttl = redis.call('TTL', key)
    if count > max_count then
        max_count = count
        retry_after = ttl
    end
end
return {max_count, retry_after}
"""


def _build_risk_manager(settings: Settings) -> RiskManager:
    return RiskManager(
        limits=RiskLimits(
            risk_per_trade=settings.risk_per_trade,
            max_position_fraction=settings.max_position_fraction,
            max_portfolio_exposure_fraction=settings.max_portfolio_exposure_fraction,
            max_open_positions=settings.max_open_positions,
            max_daily_loss_fraction=settings.max_daily_loss_fraction,
            max_drawdown_fraction=settings.max_drawdown_fraction,
            cooldown_seconds=settings.symbol_cooldown_seconds,
        ),
        enabled=settings.enable_trading,
    )


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
        application.state.risk_manager = _build_risk_manager(app_settings)
        application.state.paper_broker = PaperBroker(
            initial_cash=100_000.0,
            risk_manager=application.state.risk_manager,
        )
        try:
            if app_settings.app_env == "test":
                persisted_bars = {}
                persisted_orders = []
                persisted_portfolio = None
            else:
                async with application.state.database_session_factory() as session:
                    market_repository = MarketDataRepository(session)
                    order_repository = PaperOrderRepository(session)
                    portfolio_repository = PaperPortfolioRepository(session)
                    persisted_bars = await market_repository.list_all()
                    persisted_orders = await order_repository.list_all()
                    persisted_portfolio = await portfolio_repository.load()
            application.state.market_data_store = persisted_bars
            application.state.paper_broker.restore_orders(persisted_orders)
            if persisted_portfolio is not None:
                application.state.paper_broker.restore_state(persisted_portfolio)
            yield
        finally:
            await application.state.redis_client.aclose()
            await application.state.database_engine.dispose()

    application = FastAPI(
        title="AI Automated Trading Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.app_env = app_settings.app_env
    application.state.settings = app_settings
    allowed_origins = [
        origin.strip() for origin in app_settings.cors_allowed_origins.split(",") if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key"],
    )
    application.state.risk_manager = _build_risk_manager(app_settings)
    application.state.paper_broker = PaperBroker(
        initial_cash=100_000.0,
        risk_manager=application.state.risk_manager,
    )
    application.state.market_data_store: dict[str, list[dict[str, object]]] = {}
    application.state.strategy_decisions: dict[str, dict[str, object]] = {}
    application.state.paper_order_lock = asyncio.Lock()
    application.state.audit_events = []

    @application.middleware("http")
    async def rate_limit_api(request, call_next):
        if (
            app_settings.app_env == "test"
            or not request.url.path.startswith("/api/")
            or request.method == "OPTIONS"
        ):
            return await call_next(request)
        client_host = request.client.host if request.client is not None else "unknown"
        identities = [f"ip:{client_host}"]
        api_key = request.headers.get("x-api-key")
        if api_key:
            identities.append(f"key:{hashlib.sha256(api_key.encode()).hexdigest()}")
        redis_keys = [
            f"rate-limit:v1:{hashlib.sha256(identity.encode()).hexdigest()}"
            for identity in identities
        ]
        redis_client = getattr(application.state, "redis_client", None)
        if redis_client is None:
            return JSONResponse(
                status_code=503,
                content={"detail": "rate limit service is unavailable"},
            )
        try:
            count, retry_after = await redis_client.eval(
                _RATE_LIMIT_SCRIPT,
                len(redis_keys),
                *redis_keys,
                app_settings.rate_limit_requests,
                app_settings.rate_limit_window_seconds,
            )
        except RedisError:
            logger.exception("rate_limit_service_failed")
            return JSONResponse(
                status_code=503,
                content={"detail": "rate limit service is unavailable"},
            )
        if int(count) > app_settings.rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "request rate limit exceeded"},
                headers={
                    "Retry-After": str(max(1, int(retry_after))),
                    "X-RateLimit-Limit": str(app_settings.rate_limit_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(app_settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, app_settings.rate_limit_requests - int(count))
        )
        return response

    @application.middleware("http")
    async def audit_api_writes(request, call_next):
        if request.method not in {
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        } or not request.url.path.startswith("/api/"):
            return await call_next(request)
        request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        route = request.scope.get("route")
        event = {
            "id": str(uuid.uuid4()),
            "request_id": request_id,
            "actor": getattr(request.state, "audit_actor", "anonymous"),
            "method": request.method,
            "path": getattr(route, "path", request.url.path),
            "status_code": response.status_code,
            "created_at": datetime.now(UTC),
        }
        if app_settings.app_env == "test":
            application.state.audit_events.append(
                {**event, "created_at": event["created_at"].isoformat()}
            )
        else:
            try:
                async with application.state.database_session_factory() as session:
                    await AuditLogRepository(session).save(event)
            except SQLAlchemyError:
                logger.exception("audit_event_persist_failed request_id=%s", request_id)
        return response

    application.include_router(health_router)
    application.include_router(audit_router)
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
