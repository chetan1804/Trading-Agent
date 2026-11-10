from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from trading.broker.order import Order, OrderStatus
from trading.broker.paper_broker import PaperBroker


class ExecutionMonitor:
    def __init__(self, broker: PaperBroker, *, stale_after: timedelta | None = None) -> None:
        self.broker = broker
        self.stale_after = stale_after or timedelta(minutes=30)

    def snapshot(self) -> dict[str, object]:
        orders = list(self.broker.orders.values())
        open_orders = sum(1 for order in orders if order.status in self._active_statuses())
        filled_orders = sum(1 for order in orders if order.status in self._filled_statuses())

        fills_by_symbol: dict[str, int] = defaultdict(int)
        slippage_by_symbol: dict[str, list[float]] = defaultdict(list)
        order_health: dict[str, dict[str, object]] = {}

        for order in orders:
            health = self._health_for(order)
            order_health[order.symbol] = health

        slippage_by_execution: dict[str, float] = {}
        for execution in self.broker.executions:
            fills_by_symbol[execution.symbol] += 1
            if execution.requested_price <= 0:
                continue
            direction = 1 if execution.side == "BUY" else -1
            slippage = (
                direction
                * (execution.price - execution.requested_price)
                / execution.requested_price
                * 10_000
            )
            slippage_by_symbol[execution.symbol].append(float(slippage))
            slippage_by_execution[execution.id] = float(slippage)

        avg_fill_slippage_bps: dict[str, float] = {}
        for symbol, values in slippage_by_symbol.items():
            avg_fill_slippage_bps[symbol] = sum(values) / len(values) if values else 0.0

        stale_orders = sum(1 for order in orders if self._health_for(order)["status"] == "stale")
        recent_fills = [
            {
                "execution_id": execution.id,
                "order_id": execution.order_id,
                "symbol": execution.symbol,
                "side": execution.side,
                "quantity": execution.quantity,
                "price": execution.price,
                "fees": execution.fees,
                "slippage_bps": slippage_by_execution.get(execution.id, 0.0),
                "executed_at": self._utc_timestamp(execution.executed_at),
            }
            for execution in sorted(
                self.broker.executions,
                key=lambda item: self._sort_timestamp(item.executed_at),
                reverse=True,
            )
        ][:10]

        return {
            "open_orders": open_orders,
            "filled_orders": filled_orders,
            "fills_by_symbol": dict(fills_by_symbol),
            "avg_fill_slippage_bps": avg_fill_slippage_bps,
            "order_health": order_health,
            "stale_orders": stale_orders,
            "recent_fills": recent_fills,
        }

    @staticmethod
    def _sort_timestamp(timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=UTC)
        return timestamp.astimezone(UTC)

    @classmethod
    def _utc_timestamp(cls, timestamp: datetime) -> str:
        return cls._sort_timestamp(timestamp).isoformat()

    def _health_for(self, order: Order) -> dict[str, object]:
        now = datetime.now(UTC)
        if order.created_at.tzinfo is None:
            created_at = order.created_at.replace(tzinfo=UTC)
        else:
            created_at = order.created_at.astimezone(UTC)

        if order.status in self._filled_statuses():
            return {"status": "healthy", "order_id": order.id, "symbol": order.symbol}
        if now - created_at > self.stale_after:
            return {"status": "stale", "order_id": order.id, "symbol": order.symbol}
        return {"status": "healthy", "order_id": order.id, "symbol": order.symbol}

    @staticmethod
    def _active_statuses() -> set[OrderStatus]:
        return {
            OrderStatus.NEW,
            OrderStatus.PENDING,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        }

    @staticmethod
    def _filled_statuses() -> set[OrderStatus]:
        return {OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED}
