from fastapi import APIRouter
from pydantic import BaseModel, Field
from trading.agents.orchestrator import MarketAgent

router = APIRouter(prefix="/api", tags=["agents"])


class AgentSource(BaseModel):
    source_id: str = Field(..., min_length=1, max_length=128)
    text: str = Field(..., min_length=1, max_length=100_000)


class AgentRunRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    market_snapshot: dict[str, object] = Field(default_factory=dict)
    news: list[str] = Field(default_factory=list, max_length=100)
    documents: list[str] = Field(default_factory=list, max_length=100)
    sources: list[AgentSource] = Field(default_factory=list, max_length=100)


@router.post("/agents/run")
async def run_agent(request: AgentRunRequest) -> dict[str, object]:
    agent = MarketAgent()
    result = agent.run(
        symbol=request.symbol,
        objective=request.objective,
        market_snapshot=request.market_snapshot,
        news=request.news,
        documents=request.documents,
        research_sources=[source.model_dump() for source in request.sources],
    )
    return result
