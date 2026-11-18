import pandas as pd
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from trading.agents.orchestrator import MarketAgent
from trading.features.feature_pipeline import engineer_features

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
    snapshot: dict[str, object] = {}
    store = getattr(request.app.state, "market_data_store", {})
    bars = store.get(symbol, [])
    if bars:
        recent_bars = pd.DataFrame(bars[-300:])
        recent_bars["symbol"] = symbol
        timestamps = pd.to_datetime(recent_bars["timestamp"], utc=True).sort_values()
        interval_seconds = timestamps.diff().dt.total_seconds()
        typical_interval = interval_seconds[interval_seconds > 0].median()
        features = engineer_features(recent_bars)
        latest = features.iloc[-1]
        previous_close = float(features.iloc[-2]["close"]) if len(features) > 1 else None
        snapshot = {
            "price": float(latest["close"]),
            "volume": float(latest["volume"]),
            "timestamp": latest["timestamp"].isoformat(),
        }
        if pd.notna(typical_interval):
            snapshot["bar_interval_seconds"] = float(typical_interval)
        if previous_close:
            snapshot["change_pct"] = (float(latest["close"]) / previous_close - 1) * 100
        feature_fields = {
            "rsi": "rsi_14",
            "macd": "macd_line",
            "sma_20": "sma_20",
            "sma_50": "sma_50",
            "ema_20": "ema_20",
            "atr": "atr_14",
            "volatility": "rolling_volatility_20",
        }
        for output_name, feature_name in feature_fields.items():
            value = latest[feature_name]
            if pd.notna(value):
                snapshot[output_name] = float(value)

    snapshot.update(payload.market_snapshot)

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
        "caller+stored_bars"
        if payload.market_snapshot and bars
        else "caller"
        if payload.market_snapshot
        else "stored_bars"
        if bars
        else "unavailable"
    )
    result["data_used"]["news_source"] = (
        "caller" if payload.news else "stored_news" if headlines else "unavailable"
    )
    return result
