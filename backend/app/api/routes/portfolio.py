from fastapi import APIRouter
from trading.portfolio.manager import PortfolioManager

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.get("/portfolio/summary")
async def portfolio_summary() -> dict[str, object]:
    manager = PortfolioManager(
        cash=100_000.0,
        positions={},
        last_prices={},
        realized_pnl=0.0,
        cost_basis_by_symbol={},
    )
    snapshot = manager.snapshot()
    snapshot["status"] = "ok"
    return snapshot


@router.get("/portfolio/snapshot")
async def portfolio_snapshot() -> dict[str, object]:
    manager = PortfolioManager(
        cash=100_000.0,
        positions={},
        last_prices={},
        realized_pnl=0.0,
        cost_basis_by_symbol={},
    )
    snapshot = manager.snapshot()
    snapshot["status"] = "ok"
    return snapshot
