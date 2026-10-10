from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class TransactionCosts:
    commission_rate: float = 0.001
    fixed_commission: float = 0.0
    slippage_bps: float = 5.0
    spread_bps: float = 2.0

    def __post_init__(self) -> None:
        values = (self.commission_rate, self.fixed_commission, self.slippage_bps, self.spread_bps)
        if any(value < 0 for value in values):
            raise ValueError("transaction costs cannot be negative")
        if self.commission_rate >= 1:
            raise ValueError("commission_rate must be less than 1")

    def fill_price(self, reference_price: float, side: Literal["BUY", "SELL"]) -> float:
        if reference_price <= 0:
            raise ValueError("reference_price must be positive")
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        adverse_rate = (self.slippage_bps + self.spread_bps / 2) / 10_000
        direction = 1 if side == "BUY" else -1
        return reference_price * (1 + direction * adverse_rate)

    def commission(self, notional: float) -> float:
        if notional < 0:
            raise ValueError("notional cannot be negative")
        return notional * self.commission_rate + (self.fixed_commission if notional > 0 else 0)
