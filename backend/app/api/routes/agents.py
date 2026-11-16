from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from trading.agents.orchestrator import MarketAgent

from app.repositories.news import NewsRepository

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
async def run_agent(payload: AgentRunRequest, request: Request) -> dict[str, object]:
    """Run research with explicit inputs, filling missing market/news context locally."""
    symbol = payload.symbol.strip().upper()
    snapshot = dict(payload.market_snapshot)
    store = getattr(request.app.state, "market_data_store", {})
    bars = store.get(symbol, [])
    if bars and not snapshot:
        latest = bars[-1]
        previous = bars[-2] if len(bars) > 1 else None
        close = float(latest["close"])
        snapshot = {
            "price": close,
            "volume": float(latest["volume"]),
            "timestamp": latest["timestamp"],
        }
        if previous and float(previous["close"]) != 0:
            snapshot["change_pct"] = (close / float(previous["close"]) - 1) * 100

    headlines = list(payload.news)
    if not headlines:
        session_factory = getattr(request.app.state, "database_session_factory", None)
        if session_factory is not None:
            async with session_factory() as session:
                articles = await NewsRepository(session).list_recent(symbol, 20)
            headlines = [item["headline"] for item in articles]

    agent = MarketAgent()
    result = agent.run(
        symbol=symbol,
        objective=payload.objective,
        market_snapshot=snapshot,
        news=headlines,
        documents=payload.documents,
        research_sources=[source.model_dump() for source in payload.sources],
    )
    result["data_used"]["market_data_source"] = (
        "caller" if payload.market_snapshot else "stored_bars" if bars else "unavailable"
    )
    result["data_used"]["news_source"] = (
        "caller" if payload.news else "stored_news" if headlines else "unavailable"
    )
    return result
