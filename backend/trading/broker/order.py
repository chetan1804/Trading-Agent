from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

OrderSide = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT", "STOP"]


class OrderStatus(StrEnum):
    NEW = "NEW"
    PENDING = "PENDING"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    CANCELED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    symbol: str
    side: OrderSide
    quantity: float
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    order_type: OrderType = "MARKET"
    limit_price: float | None = None
    stop_price: float | None = None
    status: OrderStatus = OrderStatus.NEW
    filled_quantity: float = 0.0
    avg_fill_price: float | None = None
    rejection_reason: str | None = None
    id: str = field(default_factory=lambda: f"ord-{uuid.uuid4().hex[:12]}")
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        if not self.symbol or not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if not self.quantity or self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.limit_price is not None and self.limit_price <= 0:
            raise ValueError("limit price must be positive")
        if self.stop_price is not None and self.stop_price <= 0:
            raise ValueError("stop price must be positive")

    @property
    def remaining_quantity(self) -> float:
        return max(self.quantity - self.filled_quantity, 0.0)

    @property
    def is_buy(self) -> bool:
        return self.side == "BUY"

    @property
    def is_sell(self) -> bool:
        return self.side == "SELL"

    @property
    def is_active(self) -> bool:
        active_statuses = {
            OrderStatus.NEW,
            OrderStatus.PENDING,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        }
        return self.status in active_statuses

    @property
    def is_cancelled(self) -> bool:
        return self.status in {OrderStatus.CANCELLED, OrderStatus.CANCELED}

    def submit(self) -> Order:
        blocked = {
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
            OrderStatus.CANCELED,
            OrderStatus.FILLED,
        }
        if self.status in blocked:
            raise ValueError(f"cannot submit an order in status {self.status}")
        self.status = OrderStatus.OPEN
        return self

    def cancel(self) -> Order:
        if self.status is OrderStatus.FILLED:
            raise ValueError("cannot cancel a filled order")
        if self.status in {OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.CANCELED}:
            return self
        self.status = OrderStatus.CANCELLED
        return self

    def reject(self, reason: str) -> Order:
        self.status = OrderStatus.REJECTED
        self.rejection_reason = reason
        return self

    def apply_fill(self, quantity: float, price: float) -> Order:
        if self.status in {OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.CANCELED}:
            raise ValueError(f"cannot fill a {self.status.value.lower()} order")
        if self.status is OrderStatus.FILLED:
            raise ValueError("order already filled")
        if quantity <= 0:
            raise ValueError("fill quantity must be positive")
        remaining = self.remaining_quantity
        if quantity > remaining:
            raise ValueError("fill quantity exceeds remaining order quantity")
        if price <= 0:
            raise ValueError("fill price must be positive")

        new_total = self.filled_quantity + quantity
        if self.avg_fill_price is None:
            self.avg_fill_price = float(price)
        else:
            weighted_total = (self.avg_fill_price * self.filled_quantity) + (
                float(price) * quantity
            )
            self.avg_fill_price = weighted_total / new_total

        self.filled_quantity = new_total
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
        return self
