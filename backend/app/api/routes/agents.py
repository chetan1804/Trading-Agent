from fastapi import APIRouter
from pydantic import BaseModel, Field
from trading.agents.orchestrator import MarketAgent

router = APIRouter(prefix="/api", tags=["agents"])


class AgentRunRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    market_snapshot: dict[str, object] = Field(default_factory=dict)
    news: list[str] = Field(default_factory=list)


@router.post("/agents/run")
async def run_agent(request: AgentRunRequest) -> dict[str, object]:
    agent = MarketAgent()
    result = agent.run(
        symbol=request.symbol,
        objective=request.objective,
        market_snapshot=request.market_snapshot,
        news=request.news,
    )
    return result
