from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["paper-trading"])


class PaperTradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: float = Field(..., gt=0)
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT|STOP)$")
    limit_price: float | None = Field(default=None, gt=0)
    stop_price: float | None = Field(default=None, gt=0)
    reduce_only: bool = False


def _serialize_order(order: object) -> dict[str, object]:
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
        "created_at": order.created_at.isoformat(),
    }


@router.post("/paper-trading/orders")
async def create_paper_trade(request: Request, payload: PaperTradeRequest) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")

    market_price = payload.limit_price or 100.0
    order = broker.create_order(
        symbol=payload.symbol.upper(),
        side=payload.side,
        quantity=float(payload.quantity),
        order_type=payload.order_type,
        limit_price=payload.limit_price,
        stop_price=payload.stop_price,
        reduce_only=payload.reduce_only,
    )
    broker.submit_order(
        order,
        market_price=market_price,
        timestamp=datetime.now(UTC),
    )

    return _serialize_order(order)


@router.get("/paper-trading/orders")
async def list_paper_trades(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")

    orders = [
        _serialize_order(order)
        for order in broker.list_orders()
    ]
    return {"count": len(orders), "orders": orders}
