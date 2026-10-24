from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaperPortfolioRecord


class PaperPortfolioRepository:
    """Persist the single local paper-account snapshot."""

    ACCOUNT_ID = "paper"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, snapshot: dict[str, object], *, commit: bool = True) -> None:
        values = {"account_id": self.ACCOUNT_ID, **snapshot}
        statement = insert(PaperPortfolioRecord).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[PaperPortfolioRecord.account_id],
            set_={key: getattr(statement.excluded, key) for key in values if key != "account_id"},
        )
        await self.session.execute(statement)
        if commit:
            await self.session.commit()

    async def load(self) -> dict[str, object] | None:
        result = await self.session.execute(
            select(PaperPortfolioRecord).where(PaperPortfolioRecord.account_id == self.ACCOUNT_ID)
        )
        record = result.scalar_one_or_none()
        if record is None:
            return None
        return {
            "initial_cash": record.initial_cash,
            "cash": record.cash,
            "positions": record.positions,
            "last_prices": record.last_prices,
            "position_cost_basis": record.position_cost_basis,
            "realized_pnl": record.realized_pnl,
            "daily_pnl": record.daily_pnl,
            "peak_equity": record.peak_equity,
            "last_trade_at_by_symbol": record.last_trade_at_by_symbol,
        }
