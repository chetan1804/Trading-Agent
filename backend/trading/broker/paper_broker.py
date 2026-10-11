from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from trading.broker.order import Order, OrderStatus
from trading.risk.manager import AccountRiskState, RiskDecision, RiskManager, TradeProposal


class PaperBroker:
    def __init__(
        self,
        *,
        initial_cash: float = 100_000.0,
        risk_manager: RiskManager | None = None,
        fee_rate: float = 0.0005,
        slippage_bps: float = 10.0,
    ) -> None:
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.positions: dict[str, float] = {}
        self.orders: dict[str, Order] = {}
        self.last_prices: dict[str, float] = {}
        self.position_cost_basis: dict[str, float] = {}
        self.realized_pnl = 0.0
        self.risk_manager = risk_manager
        self.fee_rate = float(fee_rate)
        self.slippage_bps = float(slippage_bps)
        self.daily_pnl = 0.0
        self.peak_equity = self.initial_cash
        self.last_trade_at_by_symbol: dict[str, datetime] = {}

    @property
    def equity(self) -> float:
        position_value = sum(
            quantity * self.last_prices.get(symbol, 0.0)
            for symbol, quantity in self.positions.items()
        )
        return self.cash + position_value

    @property
    def current_exposure(self) -> float:
        return sum(
            abs(quantity) * self.last_prices.get(symbol, 0.0)
            for symbol, quantity in self.positions.items()
        )

    def create_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        limit_price: float | None = None,
        stop_price: float | None = None,
        reduce_only: bool = False,
    ) -> Order:
        order = Order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price,
        )
        self.orders[order.id] = order
        return order

    def get_order(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

    def list_orders(self) -> list[Order]:
        return list(self.orders.values())

    def submit_order(
        self,
        order: Order,
        *,
        risk_decision: RiskDecision | None = None,
        market_price: float | None = None,
        timestamp: datetime | None = None,
    ) -> Order:
        self.orders.setdefault(order.id, order)
        blocked_states = {
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
            OrderStatus.CANCELED,
            OrderStatus.FILLED,
        }
        if order.status in blocked_states:
            raise ValueError(f"cannot submit an order in status {order.status}")

        if risk_decision is not None and not risk_decision.approved:
            return order.reject(risk_decision.reason)

        if self.risk_manager is not None:
            reference_price = (
                market_price
                if market_price is not None
                else order.limit_price or self.last_prices.get(order.symbol)
            )
            if reference_price is None or reference_price <= 0:
                raise ValueError("market price must be positive for risk evaluation")
            account = self._risk_account()
            proposal = TradeProposal(
                symbol=order.symbol,
                side=order.side,
                entry_price=float(reference_price),
                timestamp=timestamp or datetime.now(UTC),
                stop_loss_price=order.stop_price,
                reduce_quantity=None,
            )
            decision = self.risk_manager.evaluate(proposal, account)
            if not decision.approved:
                return order.reject(decision.reason)

        order.submit()
        return order

    def place_order(self, *args: Any, **kwargs: Any) -> Order:
        return self.submit_order(*args, **kwargs)

    def fill_order(
        self,
        order_id: str,
        *,
        price: float,
        quantity: float | None = None,
        fees: float | None = None,
    ) -> Order:
        order = self.orders.get(order_id)
        if order is None:
            raise KeyError(f"unknown order id {order_id}")
        if order.status in {OrderStatus.REJECTED, OrderStatus.CANCELLED, OrderStatus.CANCELED}:
            raise ValueError(f"cannot fill a {order.status.value.lower()} order")
        if order.status is OrderStatus.FILLED:
            return order

        if price <= 0:
            raise ValueError("fill price must be positive")

        fill_quantity = order.remaining_quantity if quantity is None else float(quantity)
        if fill_quantity <= 0:
            raise ValueError("fill quantity must be positive")
        if fill_quantity > order.remaining_quantity:
            raise ValueError("fill quantity exceeds remaining order quantity")

        adjusted_price = float(price)
        if order.side == "BUY":
            adjusted_price *= 1 + (self.slippage_bps / 10_000)
        else:
            adjusted_price *= 1 - (self.slippage_bps / 10_000)

        order.apply_fill(fill_quantity, adjusted_price)
        fee = float(fees) if fees is not None else adjusted_price * fill_quantity * self.fee_rate
        if order.side == "BUY":
            self.cash -= (adjusted_price * fill_quantity) + fee
            current_quantity = self.positions.get(order.symbol, 0.0)
            new_quantity = current_quantity + fill_quantity
            total_basis = self.position_cost_basis.get(order.symbol, 0.0)
            self.position_cost_basis[order.symbol] = total_basis + (adjusted_price * fill_quantity)
            self.positions[order.symbol] = new_quantity
        else:
            self.cash += (adjusted_price * fill_quantity) - fee
            current = self.positions.get(order.symbol, 0.0)
            current_basis = self.position_cost_basis.get(order.symbol, 0.0)
            avg_cost = 0.0 if current <= 0 else current_basis / current
            realized = (adjusted_price - avg_cost) * fill_quantity
            self.realized_pnl += realized
            self.daily_pnl += realized
            next_position = current - fill_quantity
            if next_position == 0:
                self.positions.pop(order.symbol, None)
                self.position_cost_basis.pop(order.symbol, None)
            else:
                self.positions[order.symbol] = next_position
                self.position_cost_basis[order.symbol] = avg_cost * next_position

        self.last_prices[order.symbol] = adjusted_price
        self.peak_equity = max(self.peak_equity, self.equity)
        self.last_trade_at_by_symbol[order.symbol] = datetime.now(UTC)
        return order

    def cancel_order(self, order_id: str) -> Order:
        order = self.orders.get(order_id)
        if order is None:
            raise KeyError(f"unknown order id {order_id}")
        return order.cancel()

    def _risk_account(self) -> AccountRiskState:
        return AccountRiskState(
            equity=self.equity,
            available_cash=self.cash,
            current_exposure=self.current_exposure,
            positions=dict(self.positions),
            daily_pnl=self.daily_pnl,
            peak_equity=self.peak_equity,
            last_trade_at_by_symbol=dict(self.last_trade_at_by_symbol),
        )
