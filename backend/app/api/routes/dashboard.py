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
    performance = PerformanceAnalytics.from_paper_broker(broker)
    summary = DashboardSummary(
        portfolio=portfolio,
        performance=performance,
        execution=ExecutionMonitor(broker).snapshot(),
    ).snapshot()
    risk_manager = getattr(request.app.state, "risk_manager", None)
    if risk_manager is not None:
        summary["risk"] = risk_manager.status_snapshot(broker.risk_account())
    return summary
