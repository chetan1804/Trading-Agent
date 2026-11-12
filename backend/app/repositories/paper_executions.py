from datetime import UTC

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from trading.broker.order import Execution

from app.db.models import PaperExecutionRecord


class PaperExecutionRepository:
    """Persist individual paper fills for audit and execution reporting."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, execution: Execution, *, commit: bool = True) -> None:
        values = {
            "id": execution.id,
            "order_id": execution.order_id,
            "symbol": execution.symbol,
            "side": execution.side,
            "quantity": execution.quantity,
            "price": execution.price,
            "fees": execution.fees,
            "executed_at": execution.executed_at,
            "requested_price": execution.requested_price,
            "requested_quantity": execution.requested_quantity,
            "requested_fees": execution.requested_fees,
            "idempotency_key": execution.idempotency_key,
            "realized_pnl": execution.realized_pnl,
        }
        await self.session.execute(
            insert(PaperExecutionRecord).values(**values).on_conflict_do_nothing()
        )
        if commit:
            await self.session.commit()

    async def list_all(self, *, limit: int | None = None) -> list[Execution]:
        statement = select(PaperExecutionRecord).order_by(
            PaperExecutionRecord.executed_at, PaperExecutionRecord.id
        )
        if limit is not None:
            statement = statement.limit(limit)
        result = await self.session.execute(statement)
        executions = []
        for record in result.scalars():
            executed_at = record.executed_at
            if executed_at.tzinfo is None:
                executed_at = executed_at.replace(tzinfo=UTC)
            executions.append(
                Execution(
                    id=record.id,
                    order_id=record.order_id,
                    symbol=record.symbol,
                    side=record.side,  # type: ignore[arg-type]
                    quantity=record.quantity,
                    price=record.price,
                    fees=record.fees,
                    executed_at=executed_at,
                    requested_price=record.requested_price,
                    requested_quantity=record.requested_quantity,
                    requested_fees=record.requested_fees,
                    idempotency_key=record.idempotency_key,
                    realized_pnl=record.realized_pnl,
                )
            )
        return executions
