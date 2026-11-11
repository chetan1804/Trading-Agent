from fastapi import APIRouter, HTTPException, Request
from trading.performance.analytics import PerformanceAnalytics

router = APIRouter(prefix="/api", tags=["performance"])


@router.get("/performance/summary")
async def performance_summary(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=503, detail="paper account is unavailable")
    analytics = PerformanceAnalytics.from_paper_broker(broker)
    payload = analytics.snapshot()
    payload["status"] = "ok"
    return payload
