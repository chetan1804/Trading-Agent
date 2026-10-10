import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from trading.risk.limits import RiskLimits
from trading.risk.position_sizing import PositionSize, size_position

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradeProposal:
    symbol: str
    side: Literal["BUY", "SELL"]
    entry_price: float
    timestamp: datetime
    stop_loss_price: float | None = None
    reduce_quantity: float | None = None


@dataclass(frozen=True)
class AccountRiskState:
    equity: float
    available_cash: float
    current_exposure: float = 0.0
    positions: Mapping[str, float] = field(default_factory=dict)
    daily_pnl: float = 0.0
    peak_equity: float | None = None
    last_trade_at_by_symbol: Mapping[str, datetime] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str
    quantity: float = 0.0
    capital_required: float = 0.0
    estimated_risk: float = 0.0


class RiskManager:
    def __init__(self, limits: RiskLimits | None = None, *, enabled: bool = False) -> None:
        self.limits = limits or RiskLimits()
        self.enabled = enabled

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        logger.warning("trading_kill_switch enabled=%s", enabled)

    def evaluate(self, proposal: TradeProposal, account: AccountRiskState) -> RiskDecision:
        if not proposal.symbol.strip():
            return self._reject("symbol is required")
        if proposal.side not in ("BUY", "SELL"):
            return self._reject("side must be BUY or SELL")
        if proposal.timestamp.tzinfo is None:
            return self._reject("proposal timestamp must be timezone-aware")
        if not math.isfinite(proposal.entry_price) or proposal.entry_price <= 0:
            return self._reject("entry price must be finite and positive")
        account_values = (
            account.equity,
            account.available_cash,
            account.current_exposure,
            account.daily_pnl,
        )
        if not all(math.isfinite(value) for value in account_values):
            return self._reject("account risk values must be finite")
        if account.peak_equity is not None and not math.isfinite(account.peak_equity):
            return self._reject("peak equity must be finite")
        invalid_positions = any(
            not math.isfinite(quantity) or quantity < 0 for quantity in account.positions.values()
        )
        if invalid_positions:
            return self._reject("position quantities must be finite and non-negative")

        current_quantity = account.positions.get(proposal.symbol, 0.0)
        if proposal.side == "SELL":
            return self._evaluate_reduction(proposal, current_quantity)

        blocked_reason = self._buy_block_reason(proposal, account, current_quantity)
        if blocked_reason:
            return self._reject(blocked_reason)
        if proposal.stop_loss_price is None:
            return self._reject("a stop-loss price is required to size a new position")

        equity = account.equity
        max_exposure = equity * self.limits.max_portfolio_exposure_fraction
        max_position_notional = min(
            equity * self.limits.max_position_fraction,
            max_exposure - account.current_exposure,
        )
        if max_position_notional <= 0:
            return self._reject("maximum portfolio exposure reached")

        try:
            size = size_position(
                equity=equity,
                available_cash=account.available_cash,
                entry_price=proposal.entry_price,
                stop_loss_price=proposal.stop_loss_price,
                risk_fraction=self.limits.risk_per_trade,
                max_position_notional=max_position_notional,
            )
        except ValueError as error:
            return self._reject(str(error))
        if size.quantity <= 0:
            return self._reject("no positive position size fits the risk limits")
        return self._approve(size)

    def _buy_block_reason(
        self,
        proposal: TradeProposal,
        account: AccountRiskState,
        current_quantity: float,
    ) -> str | None:
        if not self.enabled:
            return "trading kill switch is disabled"
        if account.equity <= 0 or account.available_cash <= 0:
            return "equity and available cash must be positive"
        if account.current_exposure < 0:
            return "current exposure cannot be negative"
        if current_quantity > 0:
            return "symbol already has an open long position"
        open_positions = sum(quantity > 0 for quantity in account.positions.values())
        if open_positions >= self.limits.max_open_positions:
            return "maximum open positions reached"
        if account.daily_pnl <= -account.equity * self.limits.max_daily_loss_fraction:
            return "maximum daily loss reached"

        peak_equity = account.peak_equity if account.peak_equity is not None else account.equity
        if peak_equity <= 0:
            return "peak equity must be positive"
        drawdown_fraction = max(0.0, (peak_equity - account.equity) / peak_equity)
        if drawdown_fraction >= self.limits.max_drawdown_fraction:
            return "maximum drawdown reached"

        last_trade_at = account.last_trade_at_by_symbol.get(proposal.symbol)
        if last_trade_at is not None:
            if last_trade_at.tzinfo is None:
                return "last trade timestamp must be timezone-aware"
            elapsed = (proposal.timestamp - last_trade_at).total_seconds()
            if elapsed < 0:
                return "proposal timestamp precedes the last trade"
            if elapsed < self.limits.cooldown_seconds:
                return "symbol is in cooldown"
        return None

    def _evaluate_reduction(self, proposal: TradeProposal, current_quantity: float) -> RiskDecision:
        if current_quantity <= 0:
            return self._reject("no open position to reduce")
        quantity = (
            current_quantity if proposal.reduce_quantity is None else proposal.reduce_quantity
        )
        invalid_quantity = (
            not math.isfinite(quantity) or quantity <= 0 or quantity > current_quantity
        )
        if invalid_quantity:
            return self._reject(
                "sell quantity must be positive and no greater than the open position"
            )
        return self._approve(PositionSize(quantity, quantity * proposal.entry_price, 0.0))

    @staticmethod
    def _reject(reason: str) -> RiskDecision:
        logger.warning("risk_decision approved=false reason=%s", reason)
        return RiskDecision(approved=False, reason=reason)

    @staticmethod
    def _approve(size: PositionSize) -> RiskDecision:
        logger.info(
            "risk_decision approved=true quantity=%s estimated_risk=%s",
            size.quantity,
            size.estimated_risk,
        )
        return RiskDecision(
            approved=True,
            reason="approved",
            quantity=size.quantity,
            capital_required=size.capital_required,
            estimated_risk=size.estimated_risk,
        )
