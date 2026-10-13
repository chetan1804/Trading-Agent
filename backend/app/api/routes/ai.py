from fastapi import APIRouter
from pydantic import BaseModel, Field
from trading.ai.research import MarketResearchAssistant

router = APIRouter(prefix="/api", tags=["ai"])


class AIResearchRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    market_snapshot: dict[str, object] = Field(default_factory=dict)
    news: list[str] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)


@router.post("/ai/research")
async def ai_research(request: AIResearchRequest) -> dict[str, object]:
    assistant = MarketResearchAssistant.default()
    return assistant.generate_report(
        symbol=request.symbol,
        market_snapshot=request.market_snapshot,
        news=request.news,
        documents=request.documents,
    )
