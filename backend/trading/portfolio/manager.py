from __future__ import annotations

from typing import Any

from trading.broker.paper_broker import PaperBroker


class PortfolioManager:
    def __init__(
        self,
        *,
        cash: float = 0.0,
        positions: dict[str, float] | None = None,
        last_prices: dict[str, float] | None = None,
        realized_pnl: float = 0.0,
        cost_basis_by_symbol: dict[str, float] | None = None,
    ) -> None:
        self.cash = float(cash)
        self.positions = dict(positions or {})
        self.last_prices = dict(last_prices or {})
        self.realized_pnl = float(realized_pnl)
        self.cost_basis_by_symbol = dict(cost_basis_by_symbol or {})

    @classmethod
    def from_broker(cls, broker: PaperBroker) -> PortfolioManager:
        return cls(
            cash=broker.cash,
            positions=dict(broker.positions),
            last_prices=dict(broker.last_prices),
            realized_pnl=broker.realized_pnl,
            cost_basis_by_symbol=dict(broker.position_cost_basis),
        )

    def update_market_prices(self, prices: dict[str, float]) -> None:
        for symbol, price in prices.items():
            self.last_prices[symbol] = float(price)

    @property
    def total_value(self) -> float:
        return self.cash + self.position_value

    @property
    def position_value(self) -> float:
        return sum(
            quantity * self.last_prices.get(symbol, 0.0)
            for symbol, quantity in self.positions.items()
        )

    @property
    def exposure(self) -> float:
        return sum(
            abs(quantity) * self.last_prices.get(symbol, 0.0)
            for symbol, quantity in self.positions.items()
        )

    @property
    def unrealized_pnl(self) -> float:
        total = 0.0
        for symbol, quantity in self.positions.items():
            if quantity <= 0:
                continue
            market_price = self.last_prices.get(symbol, 0.0)
            total_basis = self.cost_basis_by_symbol.get(symbol, 0.0)
            average_cost = 0.0 if quantity == 0 else total_basis / quantity
            total += (market_price - average_cost) * quantity
        return total

    @property
    def net_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl

    @property
    def open_positions(self) -> dict[str, float]:
        return {symbol: quantity for symbol, quantity in self.positions.items() if quantity > 0}

    def snapshot(self) -> dict[str, Any]:
        return {
            "cash": self.cash,
            "positions": dict(self.positions),
            "last_prices": dict(self.last_prices),
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "net_pnl": self.net_pnl,
            "total_value": self.total_value,
            "exposure": self.exposure,
        }
