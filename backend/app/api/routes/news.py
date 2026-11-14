from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from trading.ai.news_pipeline import process_article

from app.core.security import require_api_key
from app.repositories.news import NewsRepository

router = APIRouter(prefix="/api", tags=["news"])


class NewsArticleInput(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    source: str = Field(..., min_length=1, max_length=128)
    headline: str = Field(..., min_length=1, max_length=2000)
    published_at: datetime

    @field_validator("symbol", "source", "headline", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class NewsIngestRequest(BaseModel):
    articles: list[NewsArticleInput] = Field(..., min_length=1, max_length=500)


@router.post("/news/ingest")
async def ingest_news(
    request: Request,
    payload: NewsIngestRequest,
    _auth: None = Depends(require_api_key),
) -> dict[str, int]:
    session_factory = getattr(request.app.state, "database_session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=503, detail="news storage is unavailable")

    normalized = {
        article["content_hash"]: article
        for article in (process_article(item.model_dump()) for item in payload.articles)
    }
    async with session_factory() as session:
        inserted = await NewsRepository(session).insert_many(list(normalized.values()))
    return {
        "received": len(payload.articles),
        "unique_in_batch": len(normalized),
        "inserted": inserted,
        "duplicates": len(payload.articles) - inserted,
    }


@router.get("/news")
async def list_news(
    request: Request,
    symbol: str = Query(..., min_length=1, max_length=32),
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    session_factory = getattr(request.app.state, "database_session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=503, detail="news storage is unavailable")
    async with session_factory() as session:
        articles = await NewsRepository(session).list_recent(symbol.strip().upper(), limit)
    return {"symbol": symbol.strip().upper(), "count": len(articles), "items": articles}
