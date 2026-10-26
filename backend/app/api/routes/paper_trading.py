from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field
from trading.broker.order import Order
from trading.broker.paper_broker import PaperBroker
from trading.portfolio.manager import PortfolioManager

from app.repositories.paper_orders import PaperOrderRepository
from app.repositories.paper_portfolio import PaperPortfolioRepository

router = APIRouter(prefix="/api", tags=["paper-trading"])


async def _save_order(request: Request, order: Order) -> None:
    session_factory = getattr(request.app.state, "database_session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=503, detail="paper order storage is unavailable")
    async with session_factory() as session:
        await PaperOrderRepository(session).save(order)


async def _save_fill_state(request: Request, order: Order, broker: PaperBroker) -> None:
    session_factory = getattr(request.app.state, "database_session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=503, detail="paper trading storage is unavailable")
    async with session_factory() as session:
        await PaperOrderRepository(session).save(order, commit=False)
        await PaperPortfolioRepository(session).save(broker.snapshot_state(), commit=False)
        await session.commit()


class PaperTradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: float = Field(..., gt=0, allow_inf_nan=False)
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT|STOP)$")
    limit_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    stop_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    reduce_only: bool = False


class PaperFillRequest(BaseModel):
    price: float = Field(..., gt=0, allow_inf_nan=False)
    quantity: float | None = Field(default=None, gt=0, allow_inf_nan=False)


def _serialize_order(order: Order) -> dict[str, object]:
    return {
        "id": order.id,
        "symbol": order.symbol,
        "side": order.side,
        "quantity": order.quantity,
        "status": order.status.value,
        "order_type": order.order_type,
        "filled_quantity": order.filled_quantity,
        "avg_fill_price": order.avg_fill_price,
        "limit_price": order.limit_price,
        "stop_price": order.stop_price,
        "rejection_reason": order.rejection_reason,
        "idempotency_key": order.idempotency_key,
        "created_at": order.created_at.isoformat(),
    }


@router.post("/paper-trading/orders")
async def create_paper_trade(
    request: Request,
    payload: PaperTradeRequest,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", min_length=8, max_length=128
    ),
) -> dict[str, object]:
    lock = getattr(request.app.state, "paper_order_lock", None)
    if lock is None:
        return await _create_paper_trade(request, payload, idempotency_key)
    async with lock:
        return await _create_paper_trade(request, payload, idempotency_key)


async def _create_paper_trade(
    request: Request,
    payload: PaperTradeRequest,
    idempotency_key: str | None,
) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")
    if payload.reduce_only and payload.side != "SELL":
        raise HTTPException(status_code=422, detail="reduce_only orders must use side SELL")

    symbol = payload.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=422, detail="symbol cannot be blank")
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol, [])
    market_price = payload.limit_price
    if market_price is None and stored_bars:
        market_price = float(stored_bars[-1]["close"])
    if market_price is None or market_price <= 0:
        raise HTTPException(
            status_code=422,
            detail="a positive limit price or an ingested market price is required",
        )

    try:
        order = broker.create_order(
            symbol=symbol,
            side=payload.side,
            quantity=float(payload.quantity),
            order_type=payload.order_type,
            limit_price=payload.limit_price,
            stop_price=payload.stop_price,
            reduce_only=payload.reduce_only,
            idempotency_key=idempotency_key,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if order.status.value != "NEW":
        await _save_order(request, order)
        return _serialize_order(order)
    broker.submit_order(
        order,
        market_price=market_price,
        timestamp=datetime.now(UTC),
    )
    await _save_order(request, order)

    return _serialize_order(order)


@router.post("/paper-trading/orders/{order_id}/cancel")
async def cancel_paper_trade(request: Request, order_id: str) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")
    try:
        order = broker.cancel_order(order_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="paper order not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    await _save_order(request, order)
    return _serialize_order(order)


@router.post("/paper-trading/orders/{order_id}/fill")
async def fill_paper_trade(
    request: Request,
    order_id: str,
    payload: PaperFillRequest,
) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")
    try:
        order = broker.fill_order(
            order_id,
            price=payload.price,
            quantity=payload.quantity,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="paper order not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    await _save_fill_state(request, order, broker)
    portfolio = PortfolioManager.from_broker(broker).snapshot()
    return {"order": _serialize_order(order), "portfolio": portfolio}


@router.get("/paper-trading/orders")
async def list_paper_trades(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")

    orders = [_serialize_order(order) for order in broker.list_orders()]
    return {"count": len(orders), "orders": orders}
