from fastapi import APIRouter, HTTPException, Request
from trading.portfolio.manager import PortfolioManager

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio/summary")
async def portfolio_summary(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")
    manager = PortfolioManager.from_broker(broker)
    snapshot = manager.snapshot()
    snapshot["status"] = "ok"
    return snapshot


@router.get("/portfolio/snapshot")
async def portfolio_snapshot(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=500, detail="paper broker is not initialized")
    manager = PortfolioManager.from_broker(broker)
    snapshot = manager.snapshot()
    snapshot["status"] = "ok"
    return snapshot
