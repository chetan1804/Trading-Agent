from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import StrategyDecisionRecord


class StrategyDecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, decision_id: str) -> dict[str, object] | None:
        result = await self.session.get(StrategyDecisionRecord, decision_id)
        if result is None:
            return None
        return self._serialize(result)

    async def save(self, decision: dict[str, object]) -> None:
        fields = {
            key: decision[key]
            for key in (
                "id",
                "strategy_id",
                "symbol",
                "signal_timestamp",
                "action",
                "confidence",
                "reason",
                "approved",
                "risk_reason",
                "quantity",
                "order_id",
                "created_at",
            )
        }
        statement = insert(StrategyDecisionRecord).values(**fields)
        statement = statement.on_conflict_do_nothing(index_elements=[StrategyDecisionRecord.id])
        await self.session.execute(statement)
        await self.session.commit()

    async def list_recent(self, limit: int = 100) -> list[dict[str, object]]:
        result = await self.session.execute(
            select(StrategyDecisionRecord)
            .order_by(StrategyDecisionRecord.created_at.desc())
            .limit(limit)
        )
        return [self._serialize(row) for row in result.scalars()]

    @staticmethod
    def _serialize(row: StrategyDecisionRecord) -> dict[str, object]:
        return {
            "id": row.id,
            "strategy_id": row.strategy_id,
            "symbol": row.symbol,
            "signal_timestamp": row.signal_timestamp.isoformat(),
            "action": row.action,
            "confidence": row.confidence,
            "reason": row.reason,
            "approved": row.approved,
            "risk_reason": row.risk_reason,
            "quantity": row.quantity,
            "order_id": row.order_id,
            "created_at": row.created_at.isoformat(),
        }
