from datetime import UTC, datetime
from hashlib import sha256

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from trading.broker.order import Order
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features
from trading.portfolio.manager import PortfolioManager
from trading.risk.manager import TradeProposal
from trading.strategies.moving_average import MovingAverageCrossoverStrategy

from app.core.security import require_api_key
from app.repositories.paper_orders import PaperOrderRepository
from app.repositories.strategy_decisions import StrategyDecisionRepository

router = APIRouter(prefix="/api", tags=["strategies"])


class StrategyRunRequest(BaseModel):
    symbol: str = Field(default="DEMO", min_length=1, max_length=32)
    stop_loss_fraction: float = Field(default=0.02, gt=0, lt=1)


async def _persist_decision(request: Request, payload: dict[str, object]) -> None:
    session_factory = getattr(request.app.state, "database_session_factory", None)
    if getattr(request.app.state, "app_env", "") == "test" or session_factory is None:
        decisions = getattr(request.app.state, "strategy_decisions", {})
        decisions.setdefault(str(payload["id"]), payload)
        request.app.state.strategy_decisions = decisions
        return
    async with session_factory() as session:
        await StrategyDecisionRepository(session).save(payload)


async def _get_decision(request: Request, decision_id: str) -> dict[str, object] | None:
    session_factory = getattr(request.app.state, "database_session_factory", None)
    if getattr(request.app.state, "app_env", "") == "test" or session_factory is None:
        return getattr(request.app.state, "strategy_decisions", {}).get(decision_id)
    async with session_factory() as session:
        return await StrategyDecisionRepository(session).get(decision_id)


@router.get("/strategies/generate")
async def generate_strategy_signals(
    request: Request,
    symbol: str = "DEMO",
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol.upper(), [])
    if stored_bars:
        market_data = pd.DataFrame(stored_bars)
        market_data["symbol"] = symbol.upper()
    else:
        market_data = generate_synthetic_ohlcv(
            symbol=symbol,
            periods=max(limit, 50),
            seed=7,
        )
    feature_frame = engineer_features(market_data)
    strategy = MovingAverageCrossoverStrategy(fast_window=20, slow_window=50)
    signals = strategy.generate_signals(feature_frame)
    latest = signals[-limit:]

    return {
        "symbol": symbol.upper(),
        "count": int(len(latest)),
        "strategy_id": strategy.strategy_id,
        "signals": [
            {
                "timestamp": signal.timestamp.isoformat(),
                "action": signal.action,
                "confidence": float(signal.confidence),
                "reason": signal.reason,
            }
            for signal in latest
        ],
    }


@router.post("/strategies/run")
async def run_strategy(
    request: Request,
    payload: StrategyRunRequest,
    _auth: None = Depends(require_api_key),
) -> dict[str, object]:
    """Evaluate the latest close, pass actionable signals through risk, and stage paper orders."""
    symbol = payload.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=422, detail="symbol cannot be blank")
    store = getattr(request.app.state, "market_data_store", {})
    bars = store.get(symbol, [])
    if not bars:
        raise HTTPException(status_code=422, detail="ingest market data before running a strategy")

    market_data = pd.DataFrame(bars)
    market_data["symbol"] = symbol
    features = engineer_features(market_data)
    strategy = MovingAverageCrossoverStrategy(fast_window=20, slow_window=50)
    signals = strategy.generate_signals(features)
    signal = signals[-1]
    entry_price = float(market_data.sort_values("timestamp").iloc[-1]["close"])
    decision_id = sha256(
        f"{strategy.strategy_id}:{symbol}:{signal.timestamp.isoformat()}".encode()
    ).hexdigest()
    existing = await _get_decision(request, decision_id)
    if existing is not None:
        return existing

    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")
    risk_manager = getattr(request.app.state, "risk_manager", None)
    created_at = datetime.now(UTC)
    approved = False
    risk_reason = "no actionable signal"
    quantity = 0.0
    order_id: str | None = None
    order: Order | None = None

    if signal.action in {"BUY", "SELL"}:
        stop_price = (
            entry_price * (1 - payload.stop_loss_fraction) if signal.action == "BUY" else None
        )
        proposal = TradeProposal(
            symbol=symbol,
            side=signal.action,
            entry_price=entry_price,
            timestamp=created_at,
            stop_loss_price=stop_price,
        )
        risk_decision = risk_manager.evaluate(proposal, broker.risk_account())
        approved = risk_decision.approved
        risk_reason = risk_decision.reason
        quantity = risk_decision.quantity
        if approved:
            order = broker.create_order(
                symbol=symbol,
                side=signal.action,
                quantity=quantity,
                order_type="MARKET",
                stop_price=stop_price,
                reduce_only=signal.action == "SELL",
            )
            broker.submit_order(
                order,
                risk_decision=risk_decision,
                market_price=entry_price,
                timestamp=created_at,
            )
            approved = order.status.value != "REJECTED"
            if not approved:
                risk_reason = order.rejection_reason or "paper broker rejected the order"
                quantity = 0.0
            else:
                order_id = order.id
                session_factory = getattr(request.app.state, "database_session_factory", None)
                if (
                    session_factory is not None
                    and getattr(request.app.state, "app_env", "") != "test"
                ):
                    async with session_factory() as session:
                        await PaperOrderRepository(session).save(order)

    result: dict[str, object] = {
        "id": decision_id,
        "strategy_id": signal.strategy_id,
        "symbol": symbol,
        "signal_timestamp": signal.timestamp.isoformat(),
        "action": signal.action,
        "confidence": signal.confidence,
        "reason": signal.reason,
        "reference_price": entry_price,
        "approved": approved,
        "risk_reason": risk_reason,
        "quantity": quantity,
        "order_id": order_id,
        "created_at": created_at.isoformat(),
        "order": None
        if order is None
        else {
            "id": order.id,
            "status": order.status.value,
            "side": order.side,
            "quantity": order.quantity,
            "stop_price": order.stop_price,
        },
        "execution_note": (
            "Order is staged unfilled; paper fills remain a separate explicit action."
        ),
        "portfolio": PortfolioManager.from_broker(broker).snapshot(),
    }
    await _persist_decision(request, result)
    return result


@router.get("/strategies/decisions")
async def list_strategy_decisions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    _auth: None = Depends(require_api_key),
) -> dict[str, object]:
    session_factory = getattr(request.app.state, "database_session_factory", None)
    if getattr(request.app.state, "app_env", "") == "test" or session_factory is None:
        decisions = list(getattr(request.app.state, "strategy_decisions", {}).values())
        return {"count": len(decisions), "decisions": decisions[-limit:]}
    async with session_factory() as session:
        decisions = await StrategyDecisionRepository(session).list_recent(limit)
    return {"count": len(decisions), "decisions": decisions}
