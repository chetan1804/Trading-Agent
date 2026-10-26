from datetime import UTC

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from trading.broker.order import Order, OrderStatus

from app.db.models import PaperOrderRecord


class PaperOrderRepository:
    """Store paper order state and reconstruct domain orders after restart."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, order: Order, *, commit: bool = True) -> None:
        values = {
            "id": order.id,
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "created_at": order.created_at,
            "order_type": order.order_type,
            "limit_price": order.limit_price,
            "stop_price": order.stop_price,
            "status": order.status.value,
            "filled_quantity": order.filled_quantity,
            "avg_fill_price": order.avg_fill_price,
            "rejection_reason": order.rejection_reason,
            "idempotency_key": order.idempotency_key,
        }
        statement = insert(PaperOrderRecord).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[PaperOrderRecord.id],
            set_={key: getattr(statement.excluded, key) for key in values if key != "id"},
        )
        await self.session.execute(statement)
        if commit:
            await self.session.commit()

    async def list_all(self) -> list[Order]:
        result = await self.session.execute(
            select(PaperOrderRecord).order_by(PaperOrderRecord.created_at, PaperOrderRecord.id)
        )
        orders = []
        for record in result.scalars():
            created_at = record.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            orders.append(
                Order(
                    id=record.id,
                    symbol=record.symbol,
                    side=record.side,  # type: ignore[arg-type]
                    quantity=record.quantity,
                    created_at=created_at,
                    order_type=record.order_type,  # type: ignore[arg-type]
                    limit_price=record.limit_price,
                    stop_price=record.stop_price,
                    status=OrderStatus(record.status),
                    filled_quantity=record.filled_quantity,
                    avg_fill_price=record.avg_fill_price,
                    rejection_reason=record.rejection_reason,
                    idempotency_key=record.idempotency_key,
                )
            )
        return orders
