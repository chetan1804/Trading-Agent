from collections import defaultdict
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MarketBar


class MarketDataRepository:
    """Persist and retrieve OHLCV bars using symbol/timestamp as the natural key."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_many(self, bars: list[dict[str, object]]) -> None:
        if not bars:
            return
        statement = insert(MarketBar).values(bars)
        statement = statement.on_conflict_do_update(
            index_elements=[MarketBar.symbol, MarketBar.timestamp],
            set_={
                column: getattr(statement.excluded, column)
                for column in ("open", "high", "low", "close", "volume")
            },
        )
        await self.session.execute(statement)
        await self.session.commit()

    async def list_all(self) -> dict[str, list[dict[str, object]]]:
        result = await self.session.execute(
            select(MarketBar).order_by(MarketBar.symbol, MarketBar.timestamp)
        )
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
        for bar in result.scalars():
            timestamp = bar.timestamp
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            grouped[bar.symbol].append(
                {
                    "timestamp": timestamp.isoformat(),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume),
                }
            )
        return dict(grouped)
