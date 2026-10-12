from fastapi import APIRouter
from trading.dashboard.summary import DashboardSummary

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/overview")
async def dashboard_overview() -> dict[str, object]:
    return DashboardSummary.default().snapshot()
