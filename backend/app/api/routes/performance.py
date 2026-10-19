from fastapi import APIRouter

from trading.performance.analytics import PerformanceAnalytics

router = APIRouter(prefix="/api", tags=["performance"])


@router.get("/performance/summary")
async def performance_summary() -> dict[str, object]:
    analytics = PerformanceAnalytics(
        {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "trade_count": 0,
        },
        final_equity=100_000.0,
    )
    payload = analytics.snapshot()
    payload["status"] = "ok"
    return payload
