from datetime import UTC

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NewsArticle


class NewsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_many(self, articles: list[dict[str, object]]) -> int:
        if not articles:
            return 0
        statement = (
            insert(NewsArticle)
            .values(articles)
            .on_conflict_do_nothing(constraint="uq_news_articles_content_hash")
        )
        result = await self.session.execute(statement)
        await self.session.commit()
        return int(result.rowcount or 0)

    async def list_recent(self, symbol: str, limit: int) -> list[dict[str, object]]:
        result = await self.session.execute(
            select(NewsArticle)
            .where(NewsArticle.symbol == symbol)
            .order_by(NewsArticle.published_at.desc(), NewsArticle.id)
            .limit(limit)
        )
        records = []
        for article in result.scalars():
            published_at = article.published_at
            if published_at.tzinfo is None:
                published_at = published_at.replace(tzinfo=UTC)
            records.append(
                {
                    "id": article.id,
                    "symbol": article.symbol,
                    "source": article.source,
                    "headline": article.headline,
                    "published_at": published_at.isoformat(),
                    "sentiment": article.sentiment,
                    "score": article.sentiment_score,
                    "confidence": article.confidence,
                }
            )
        return records
