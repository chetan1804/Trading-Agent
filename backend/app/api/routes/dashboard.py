from fastapi import APIRouter, HTTPException, Request
from trading.dashboard.summary import DashboardSummary
from trading.monitoring.execution import ExecutionMonitor
from trading.performance.analytics import PerformanceAnalytics
from trading.portfolio.manager import PortfolioManager

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/overview")
async def dashboard_overview(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=503, detail="paper account is unavailable")

    portfolio = PortfolioManager.from_broker(broker)
    total_return = (
        (broker.equity / broker.initial_cash) - 1
        if broker.initial_cash > 0
        else 0.0
    )
    performance = PerformanceAnalytics(
        {"total_return": total_return},
        final_equity=broker.equity,
    )
    return DashboardSummary(
        portfolio=portfolio,
        performance=performance,
        execution=ExecutionMonitor(broker).snapshot(),
    ).snapshot()
