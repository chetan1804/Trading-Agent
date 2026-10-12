from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from trading.backtesting.engine import BacktestResult
from trading.backtesting.metrics import calculate_performance_metrics


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
