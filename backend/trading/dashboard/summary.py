from __future__ import annotations

from typing import Any

from trading.performance.analytics import PerformanceAnalytics
from trading.portfolio.manager import PortfolioManager


class DashboardSummary:
    def __init__(
        self,
        *,
        portfolio: PortfolioManager | None = None,
        performance: PerformanceAnalytics | None = None,
        execution: Any | None = None,
    ) -> None:
        self.portfolio = portfolio or PortfolioManager()
        self.performance = performance
        self.execution = execution

    @classmethod
    def default(cls) -> DashboardSummary:
        return cls(
            portfolio=PortfolioManager(cash=100_000.0),
            performance=PerformanceAnalytics({"total_return": 0.0}, final_equity=100_000.0),
            execution={
                "open_orders": 0,
                "filled_orders": 0,
                "fills_by_symbol": {},
                "avg_fill_slippage_bps": {},
                "order_health": {},
                "stale_orders": 0,
            },
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "portfolio": self.portfolio.snapshot(),
            "performance": self.performance.snapshot() if self.performance else {},
            "execution": self.execution if self.execution is not None else {},
        }
