from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from trading.backtesting.engine import BacktestResult
from trading.backtesting.metrics import calculate_performance_metrics
from trading.broker.paper_broker import PaperBroker


@dataclass(frozen=True)
class PerformanceReport:
    metrics: dict[str, Any]
    final_equity: float

    def snapshot(self) -> dict[str, Any]:
        payload = dict(self.metrics)
        payload["final_equity"] = self.final_equity
        return payload


class PerformanceAnalytics:
    def __init__(self, metrics: dict[str, Any], *, final_equity: float) -> None:
        self.metrics = dict(metrics)
        self.final_equity = float(final_equity)

    @classmethod
    def from_backtest(cls, result: BacktestResult) -> PerformanceAnalytics:
        metrics = calculate_performance_metrics(result.equity_curve, result.trades)
        return cls(metrics, final_equity=result.ending_equity)

    @classmethod
    def from_paper_broker(
        cls,
        broker: PaperBroker,
        equity_history: list[dict[str, Any]] | None = None,
    ) -> PerformanceAnalytics:
        """Build account metrics and derive risk metrics only from recorded history."""
        initial_cash = broker.initial_cash
        equity = broker.equity
        metrics: dict[str, Any] = {
            "total_return": equity / initial_cash - 1 if initial_cash > 0 else 0.0,
            "realized_pnl": broker.realized_pnl,
            "unrealized_pnl": broker.unrealized_pnl,
            "execution_count": len(broker.executions),
            "exit_fill_count": sum(item.side == "SELL" for item in broker.executions),
            "total_fees": sum(item.fees for item in broker.executions),
            "open_positions": sum(quantity > 0 for quantity in broker.positions.values()),
        }
        if equity_history:
            history = pd.DataFrame(equity_history)
            history["timestamp"] = pd.to_datetime(history["captured_at"], utc=True)
            daily = (
                history.sort_values("timestamp")
                .set_index("timestamp")[["equity", "exposure"]]
                .resample("1D")
                .last()
                .dropna()
                .reset_index()
            )
            metrics["history_observations"] = int(len(daily))
            if len(daily) >= 2:
                historical_metrics = calculate_performance_metrics(daily, pd.DataFrame())
                metrics["sharpe_ratio"] = historical_metrics["sharpe_ratio"]
                metrics["max_drawdown"] = historical_metrics["max_drawdown"]
                metrics["cagr"] = historical_metrics["cagr"]
        return cls(metrics, final_equity=equity)

    @classmethod
    def from_equity_curve(
        cls,
        equity_curve: pd.DataFrame,
        trades: pd.DataFrame | None = None,
    ) -> PerformanceAnalytics:
        trade_frame = trades if trades is not None else pd.DataFrame()
        metrics = calculate_performance_metrics(equity_curve, trade_frame)
        return cls(metrics, final_equity=float(equity_curve["equity"].iloc[-1]))

    def snapshot(self) -> dict[str, Any]:
        payload = dict(self.metrics)
        payload["final_equity"] = self.final_equity
        return payload
