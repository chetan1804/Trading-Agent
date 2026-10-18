from fastapi import APIRouter
from pydantic import BaseModel, Field
from trading.ai.rag import RAGResearchAssistant
from trading.ai.research import MarketResearchAssistant
from trading.ai.sentiment import SentimentAnalyzer

router = APIRouter(prefix="/api", tags=["ai"])


class AIResearchRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    market_snapshot: dict[str, object] = Field(default_factory=dict)
    news: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)


class RAGRequest(BaseModel):
    query: str = Field(..., min_length=1)
    documents: list[str] = Field(default_factory=list)


class SentimentRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    headlines: list[str] = Field(default_factory=list)


@router.post("/ai/research")
async def ai_research(request: AIResearchRequest) -> dict[str, object]:
    assistant = MarketResearchAssistant.default()
    return assistant.generate_report(
        symbol=request.symbol,
        market_snapshot=request.market_snapshot,
        news=request.news,
        documents=request.documents,
    )


@router.post("/ai/sentiment")
async def ai_sentiment(request: SentimentRequest) -> dict[str, object]:
    analyzer = SentimentAnalyzer()
    analysis = analyzer.analyze(request.headlines)
    return {
        "symbol": request.symbol.upper(),
        "sentiment": analysis["sentiment"],
        "score": analysis["score"],
        "headline_count": analysis["headline_count"],
        "signals": analysis["signals"],
    }


@router.post("/ai/rag")
async def ai_rag(request: RAGRequest) -> dict[str, object]:
    assistant = RAGResearchAssistant()
    return assistant.answer(query=request.query, documents=request.documents)
