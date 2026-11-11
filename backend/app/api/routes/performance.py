from fastapi import APIRouter, HTTPException, Request
from trading.performance.analytics import PerformanceAnalytics

router = APIRouter(prefix="/api", tags=["performance"])


@router.get("/performance/summary")
async def performance_summary(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=503, detail="paper account is unavailable")
    history = getattr(request.app.state, "paper_equity_history", [])
    analytics = PerformanceAnalytics.from_paper_broker(broker, history)
    payload = analytics.snapshot()
    payload["status"] = "ok"
    return payload
