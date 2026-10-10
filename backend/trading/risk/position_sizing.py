import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSize:
    quantity: float
    capital_required: float
    estimated_risk: float


def size_position(
    *,
    equity: float,
    available_cash: float,
    entry_price: float,
    stop_loss_price: float,
    risk_fraction: float,
    max_position_notional: float,
) -> PositionSize:
    """Size a long position by stop distance, exposure ceiling, and available cash."""
    values = (
        equity,
        available_cash,
        entry_price,
        stop_loss_price,
        risk_fraction,
        max_position_notional,
    )
    if not all(math.isfinite(value) for value in values):
        raise ValueError("position-sizing inputs must be finite")
    if equity <= 0 or available_cash <= 0:
        raise ValueError("equity and available_cash must be positive")
    if entry_price <= 0 or stop_loss_price <= 0 or stop_loss_price >= entry_price:
        raise ValueError("a long position requires a positive stop below the entry price")
    if not 0 < risk_fraction <= 1:
        raise ValueError("risk_fraction must be greater than 0 and at most 1")
    if max_position_notional <= 0:
        raise ValueError("max_position_notional must be positive")

    risk_budget = equity * risk_fraction
    risk_per_unit = entry_price - stop_loss_price
    quantity_by_risk = risk_budget / risk_per_unit
    quantity_by_notional = max_position_notional / entry_price
    quantity_by_cash = available_cash / entry_price
    quantity = min(quantity_by_risk, quantity_by_notional, quantity_by_cash)
    capital_required = quantity * entry_price
    estimated_risk = quantity * risk_per_unit
    return PositionSize(quantity, capital_required, estimated_risk)
