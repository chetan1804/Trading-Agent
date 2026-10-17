from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field
from trading.risk.manager import AccountRiskState, RiskManager, TradeProposal

router = APIRouter(prefix="/api", tags=["risk"])


class AccountStateRequest(BaseModel):
    equity: float
    available_cash: float
    current_exposure: float = 0.0
    positions: dict[str, float] = Field(default_factory=dict)
    daily_pnl: float = 0.0
    peak_equity: float | None = None
    last_trade_at_by_symbol: dict[str, datetime] = Field(default_factory=dict)


class RiskEvaluationRequest(BaseModel):
    enabled: bool = False
    symbol: str
    side: str
    entry_price: float
    timestamp: datetime | None = None
    stop_loss_price: float | None = None
    reduce_quantity: float | None = None
    account: AccountStateRequest


@router.post("/risk/evaluate")
async def evaluate_risk(request: RiskEvaluationRequest) -> dict[str, object]:
    proposal = TradeProposal(
        symbol=request.symbol.strip(),
        side=request.side.upper(),
        entry_price=request.entry_price,
        timestamp=request.timestamp or datetime.now(UTC),
        stop_loss_price=request.stop_loss_price,
        reduce_quantity=request.reduce_quantity,
    )
    account = AccountRiskState(
        equity=request.account.equity,
        available_cash=request.account.available_cash,
        current_exposure=request.account.current_exposure,
        positions=request.account.positions,
        daily_pnl=request.account.daily_pnl,
        peak_equity=request.account.peak_equity,
        last_trade_at_by_symbol=request.account.last_trade_at_by_symbol,
    )
    decision = RiskManager(enabled=request.enabled).evaluate(proposal, account)
    return {
        "approved": decision.approved,
        "reason": decision.reason,
        "quantity": decision.quantity,
        "capital_required": decision.capital_required,
        "estimated_risk": decision.estimated_risk,
    }
